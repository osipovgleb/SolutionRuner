"""Annual capitalization: known growth factors or a rate inferred from deposits."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from ..calculus.common import answer, real_roots
from ..probability.common import UnsupportedCondition, finish, line
from . import math_common
from .math_common import number, primitive

X = sp.Symbol("x", real=True)
_MONEY = rf"(?:{VALUE}|\d+(?: \d{{3}})+)"
_PATTERN = re.compile(
    rf"Клиент А\. сделал вклад в банке в размере (?P<capital>{_MONEY}) рублей\. Проценты по вкладу начисляются раз в год и прибавляются к текущей сумме вклада\. Ровно через год на тех же условиях такой же вклад в том же банке сделал (?:клиент )?Б\. Еще ровно через год клиенты А\. и Б\. закрыли вклады и забрали все накопившиеся деньги\. При этом клиент А\. получил на (?P<difference>{_MONEY}) рубл(?:ей|я|ь) больше клиента Б\. Какой процент годовых начислял банк по этим вкладам\?"
)


@dataclass(frozen=True)
class Analysis:
    capital: sp.Rational
    difference: sp.Rational
    roots: tuple
    factor: sp.Rational
    result: sp.Rational


def calculate(context):
    data = math_common.read(context)
    match = _PATTERN.fullmatch(data[3])
    if not match:
        from .yearly_growth import analyze

        return data, analyze(data[3])
    capital, difference = (
        scalar(match[key].replace(" ", "")) for key in ["capital", "difference"]
    )
    if capital <= 0 or difference <= 0:
        raise UnsupportedCondition(
            "positive principal and difference of proceeds are required"
        )
    roots = tuple(
        sorted(real_roots(capital * (X**2 - X) - difference, X), reverse=True)
    )
    valid = [root for root in roots if root > 0]
    if len(valid) != 1 or valid[0].is_Rational is not True:
        raise UnsupportedCondition(
            "one exact rational positive annual factor is required without rounding"
        )
    factor = valid[0]
    return data, Analysis(capital, difference, roots, factor, 100 * (factor - 1))


def proof(a):
    from .yearly_growth import Analysis as Growth
    from .yearly_growth_proof import proof as growth_proof

    if isinstance(a, Growth):
        return growth_proof(a)
    html = "<p>Пусть банк начисляет p процентов годовых. Первый вклад работает два года, а второй — один год. Введём общий годовой множитель:</p>"
    html += line(
        r"S_{\mathrm{А}}="
        + number(a.capital)
        + r"\left(1+\frac{p}{100}\right)^2,\quad S_{\mathrm{Б}}="
        + number(a.capital)
        + r"\left(1+\frac{p}{100}\right)"
    )
    html += line(r"x=1+\frac{p}{100}>0")
    html += line(
        number(a.capital) + "x^2-" + number(a.capital) + "x=" + number(a.difference)
    )
    html += "<p>Решим квадратное уравнение, выражающее указанную разность полученных сумм:</p>"
    poly = sp.Poly(primitive(a.capital * (X**2 - X) - a.difference, (X,)), X)
    b, c, d = poly.nth(2), poly.nth(1), poly.nth(0)
    discriminant = c * c - 4 * b * d
    html += line(sp.latex(poly.as_expr()) + "=0")
    html += line(
        "D=("
        + number(c)
        + ")^2-4\\cdot("
        + number(b)
        + ")\\cdot("
        + number(d)
        + ")="
        + number(discriminant)
    )
    html += line(
        r"x=\frac{-("
        + number(c)
        + r")\pm\sqrt{"
        + number(discriminant)
        + "}}{2\\cdot("
        + number(b)
        + r")}\in\left\{"
        + ";".join(number(root) for root in a.roots)
        + r"\right\}"
    )
    html += "<p>Годовой множитель положителен, поэтому отрицательный корень не подходит. Найдём процент годовых:</p>"
    html += line("x=" + number(a.factor))
    return html + line("p=100(" + number(a.factor) + "-1)=" + number(a.result))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), proof(a))
