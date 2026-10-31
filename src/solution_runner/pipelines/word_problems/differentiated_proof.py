"""Retain the parents' formula method and their full schedule method, in order."""

import sympy as sp

from ..probability.common import line
from .loan_reference import reference
from .math_common import number as n
from .motion_chase_proof import section


def maximum_term(a):
    s, i, m = a.question.capital, a.rate / 100, a.question.target
    html = "<p>Первый платёж наибольший: он включает ту же часть основного долга, что и остальные, и проценты на самый большой остаток. Пусть n — срок кредита в годах:</p>"
    html += line(r"P_1=\frac{S}{n}+\frac{r}{100}S")
    html += line(r"\frac{" + n(s) + "}{n}+" + n(i * s) + "=" + n(m))
    html += line(
        r"\frac{" + n(s) + "}{n}=" + n(m) + "-" + n(i * s) + "=" + n(m - i * s)
    )
    return html + line(r"n=\frac{" + n(s) + "}{" + n(m - i * s) + "}=" + str(a.periods))


def interest_sum():
    html = "<p>Проценты начисляются на остатки долга S, S(n−1)/n, …, S/n. Обозначим эти остатки через Bⱼ. Это арифметическая прогрессия. Её сумма и общая переплата равны:</p>"
    html += line(
        r"\sum_{j=0}^{n-1}B_j=\frac{n}{2}\left(S+\frac{S}{n}\right)=\frac{S(n+1)}{2}"
    )
    html += line(r"\Pi=\frac{r}{100}\sum_{j=0}^{n-1}B_j=\frac{rS(n+1)}{200}")
    return html


def from_total(a):
    s, total = a.question.capital, a.question.target
    interest = total - s
    html = "<p>Переплата равна разности общей суммы выплат и суммы кредита. Найдём срок по формуле переплаты:</p>"
    html += line(r"\Pi=" + n(total) + "-" + n(s) + "=" + n(interest))
    coefficient = a.rate * s / 200
    html += line(n(interest) + "=" + n(coefficient) + "(n+1)")
    html += line(
        r"n+1=\frac{"
        + n(interest)
        + "}{"
        + n(coefficient)
        + "}="
        + n(sp.Integer(a.periods + 1))
    )
    return html + line("n=" + str(a.periods + 1) + "-1=" + str(a.periods))


def total_payment(a):
    s = a.question.capital
    html = "<p>Всего возвращается основной долг и проценты на остатки. Подставим найденный срок:</p>"
    html += line(r"V=S+\frac{rS(n+1)}{200}")
    html += line(
        "V="
        + n(s)
        + r"+\frac{"
        + n(a.rate)
        + r"\cdot"
        + n(s)
        + r"\cdot("
        + str(a.periods)
        + "+1)}{200}"
    )
    return html + line(
        "V=" + n(s) + "+" + n(a.total - s) + "=" + n(a.total) + r"\text{ млн руб.}"
    )


def schedule_method(a):
    s = a.question.capital
    k = 1 + a.rate / 100
    html = "<p>Долг в июле уменьшается равномерно до нуля. Обозначим его остаток после j-го платежа через Bⱼ:</p>"
    html += line(r"B_j=\frac{S(n-j)}{n},\quad j=0,1,\ldots,n")
    html += line(
        r"B_0="
        + n(s)
        + r",\quad B_1=\frac{"
        + n(s)
        + r"(n-1)}{n},\quad\ldots,\quad B_{n-1}=\frac{"
        + n(s)
        + r"}{n},\quad B_n=0"
    )
    html += "<p>В январе остаток умножается на годовой множитель, а очередной платёж уменьшает его до следующего июльского остатка:</p>"
    html += line(r"k=1+\frac{" + n(a.rate) + "}{100}=" + n(k))
    html += line(r"P_j=kB_{j-1}-B_j=\frac{S}{n}+\frac{rS}{100n}(n-j+1)")
    if a.question.kind == "maximum":
        html += maximum_term(a)
    html += "<p>Сложим все платежи: основной долг возвращается полностью, а проценты складываются по арифметической прогрессии:</p>"
    html += line(r"V=S+\frac{rS}{100n}(n+(n-1)+\ldots+1)")
    html += line(r"1+2+\ldots+n=\frac{n(n+1)}2,\qquad V=S+\frac{rS(n+1)}{200}")
    return html + (total_payment(a) if a.question.kind == "maximum" else from_total(a))


def rate_bound(a):
    s, n_years, target = a.question.capital, a.periods, a.question.target
    d = s / n_years
    k = 1 + a.rate / 100
    html = "<p>Долг уменьшается каждый июль на одну и ту же сумму. В последнем году до начисления процентов остаётся одна такая часть, и последний платёж погашает её вместе с процентами:</p>"
    html += line(r"d=\frac{S}{n}=\frac{" + n(s) + "}{" + str(n_years) + "}=" + n(d))
    html += line(r"k=1+\frac{r}{100},\qquad P_n=dk")
    html += "<p>По условию последний платёж должен быть не меньше указанной суммы:</p>"
    html += line(n(d) + "k\\geq" + n(target))
    html += line(r"k\geq\frac{" + n(target) + "}{" + n(d) + "}=" + n(k))
    html += line("r=100(k-1)\\geq100(" + n(k) + "-1)=" + n(a.rate))
    html += (
        "<p>Наименьшая ставка достигается при равенстве в полученном ограничении:</p>"
    )
    return html + line("r=" + n(a.result))


def proof(a, content):
    if a.question.kind == "rate_bound":
        return section(rate_bound(a), "Решение"), ()
    link, keys = reference(content)
    if a.question.kind == "maximum":
        first = maximum_term(a) + interest_sum() + total_payment(a)
        title = "Приведём авторское решение."
    else:
        first = interest_sum() + from_total(a)
        title = "Приведем другое решение."
    return section(first + link, "Решение") + section(schedule_method(a), title), keys
