"""Preserve the five-year table and derive the final-minus-first payment."""

from ..probability.common import line
from .debt_schedule_proof import table
from .grace_credit import multiplier
from .math_common import fraction
from .math_common import number as n
from .water_season_proof import inline


def proof(a):
    q, k = a.question, a.factor
    interest = q.rate / 100
    rows = [(str(q.year), "", "", inline("S"))]
    for j in range(1, q.grace + 1):
        rows.append(
            (
                str(q.year + j),
                inline("S\\cdot" + n(k)),
                inline(n(interest) + "S"),
                inline("S"),
            )
        )
    rows.append(
        (str(q.year + 4), inline("S\\cdot" + n(k)), inline("x"), inline(n(k) + "S-x"))
    )
    rows.append(
        (
            str(q.year + 5),
            inline("(" + n(k) + "S-x)\\cdot" + n(k)),
            inline("x"),
            inline("0"),
        )
    )
    html = (
        "<p>Пусть платежи в "
        + str(q.year + 4)
        + " и "
        + str(q.year + 5)
        + " годах равны x "
        + q.unit
        + " Сумма кредита равна S. В первые три года долг в июле остаётся равным первоначальной сумме, поэтому выплачиваются только начисленные проценты. Заполним таблицу:</p>"
    )
    html += line(
        "S=" + n(a.capital) + r",\qquad k=1+\frac{" + n(q.rate) + "}{100}=" + n(k)
    )
    html += table(
        rows,
        (
            "Год",
            "Долг в январе, " + q.unit,
            "Выплата, " + q.unit,
            "Долг в июле, " + q.unit,
        ),
    )
    html += "<p>Из последней строки получаем уравнение полного погашения:</p>"
    html += line("(" + n(k) + "S-x)\\cdot" + n(k) + "-x=0")
    html += line(n(k * k) + "S-" + n(k) + "x-x=0")
    html += line(n(k + 1) + "x=" + n(k * k) + "S")
    html += line(
        "x="
        + fraction(n(k * k) + r"\cdot" + n(a.capital), n(k + 1))
        + "="
        + n(a.payment)
    )
    first = a.capital * interest
    difference = a.payment - first
    html += "<p>Первый платёж равен процентам на исходный долг. Последний платёж больше первого, поскольку:</p>"
    html += line(r"x-(k-1)S=\frac{k^2S-(k-1)(k+1)S}{k+1}=\frac{S}{k+1}>0")
    html += line("P_1=" + n(interest) + r"\cdot" + n(a.capital) + "=" + n(first))
    html += "<p>Найдём разницу между последним и первым платежами:</p>"
    html += line(
        "x-P_1="
        + n(a.payment)
        + "-"
        + n(first)
        + "="
        + n(difference)
        + r"\text{ "
        + q.unit
        + "}"
    )
    if q.scale != 1:
        html += "<p>Выразим разницу в единицах, указанных в вопросе:</p>"
        html += line(
            n(difference)
            + r"\cdot"
            + n(q.scale)
            + "="
            + n(a.result)
            + r"\text{ "
            + ("руб." if q.scale == multiplier(q.unit) else "млн руб.")
            + "}"
        )
    return html
