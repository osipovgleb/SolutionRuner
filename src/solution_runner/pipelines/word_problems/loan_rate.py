"""Infer one positive annual rate from two specified, potentially unequal payments."""

import re

import sympy as sp

from ..applied.physical_questions import scalar
from ..calculus.common import real_roots
from .common import UnsupportedCondition
from .loan_schedule import balances
from .yearly_growth import _MONEY, _NAME

JULY = rf"В июле (?P<year>\d{{4}}) года планируется взять кредит в банке на сумму (?P<capital>{_MONEY}) рублей\. Условия возврата таковы: — каждый январь долг увеличивается на r\s*% по сравнению с концом предыдущего года; — с февраля по июнь каждого года необходимо выплатить одним платежом часть долга\. Найдите r, если известно, что кредит будет полностью погашен за два года, причем в первый год будет выплачено (?P<first>{_MONEY}) рублей, а второй год — (?P<last>{_MONEY}) рублей\."
DECEMBER = rf"31 декабря (?P<year>\d{{4}}) года (?P<name>{_NAME}) взял в банке (?P<capital>{_MONEY}) млн рублей в кредит\. Схема выплаты кредита следующая: 31 декабря каждого следующего года банк начисляет проценты на оставшуюся сумму долга\(то есть увеличивает долг на определенное количество процентов\), затем (?P=name) переводит очередной платеж\. (?P=name) выплатил кредит за два платежа, переводя в первый раз (?P<first>{_MONEY}) тыс\. рублей, во второй — (?P<last>{_MONEY}) тыс\. рублей\. Под какой процент банк выдал кредит (?P<recipient>{_NAME})\?"


def parse(text):
    from .partial_credit_questions import Question

    matches = [
        (kind, m)
        for kind, p in (("july", JULY), ("december", DECEMBER))
        if (m := re.fullmatch(p, text))
    ]
    if not matches:
        return None
    kind, m = matches[0]
    if kind == "december" and m["recipient"] != (
        m["name"][:-1] + "ю" if m["name"].endswith("ий") else m["name"] + "у"
    ):
        raise UnsupportedCondition(
            "the requested borrower must match the December loan recipient"
        )
    capital, first, last = (
        scalar(m[key].replace(" ", "")) for key in ("capital", "first", "last")
    )
    if kind == "december":
        capital *= 1_000_000
        first *= 1000
        last *= 1000
    if min(capital, first, last) <= 0:
        raise UnsupportedCondition(
            "the principal and both annual payments must be positive"
        )
    return Question("rate", int(m["year"]), None, capital, first, last, None, 1)


def equation(q):
    b = sp.Symbol("b", real=True)
    return b, q.capital * b * b - q.payment * b - q.last


def analyze(q):
    from .partial_credit import Analysis

    b, expression = equation(q)
    roots = tuple(real_roots(expression, b))
    candidates = [v for v in roots if v > 1]
    if len(candidates) != 1 or candidates[0].is_Rational is not True:
        raise UnsupportedCondition(
            "the payments must determine one positive exact rational interest rate"
        )
    k = candidates[0]
    debts = balances(q.capital, k, (q.payment, q.last))
    rate = 100 * (k - 1)
    return Analysis(
        q, q.capital, q.payment, q.last, k, debts, q.payment + q.last, rate, roots
    )


def proof(a):
    from ..probability.common import line
    from .math_common import fraction, primitive
    from .math_common import number as n

    q = a.question
    b, expression = equation(q)
    poly = sp.Poly(primitive(expression, (b,)), b)
    A, B, C = poly.all_coeffs()
    discriminant = B * B - 4 * A * C
    html = "<p>Каждый год долг увеличивается на r процентов, затем уменьшается на сумму ежегодного платежа. Выразим все суммы в рублях. Для удобства обозначим годовой множитель через b:</p>"
    html += line(r"b=1+\frac{r}{100},\qquad b>1")
    html += line("B_1=" + n(q.capital) + "b-" + n(q.payment))
    html += "<p>После второй выплаты кредит погашен полностью, поэтому второй остаток равен нулю:</p>"
    html += line(
        "B_2=(" + n(q.capital) + "b-" + n(q.payment) + ")b-" + n(q.last) + "=0"
    )
    html += line(sp.latex(poly.as_expr()) + "=0")
    html += "<p>Решим полученное квадратное уравнение:</p>"
    html += line(
        "D=(" + n(B) + r")^2-4\cdot" + n(A) + r"\cdot(" + n(C) + ")=" + n(discriminant)
    )
    html += line(
        "b=" + fraction(n(-B) + r"\pm\sqrt{" + n(discriminant) + "}", n(2 * A))
    )
    html += line("b_1=" + n(a.roots[0]) + r",\qquad b_2=" + n(a.roots[1]))
    html += "<p>Отрицательный корень не подходит: при увеличении долга множитель b больше единицы. Подставим положительный корень и найдём ставку:</p>"
    return html + line("r=100(b-1)=100(" + n(a.factor) + "-1)=" + n(a.result))
