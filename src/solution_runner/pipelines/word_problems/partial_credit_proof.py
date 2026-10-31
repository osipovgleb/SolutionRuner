"""Retain the parents' annual debt progression and their table when used."""

from ..probability.common import line
from .annuity_proof import factor
from .math_common import fraction
from .math_common import number as n
from .motion_chase_proof import section
from .water_season_proof import inline


def expression(capital, coefficient, payment, weight):
    base = n(coefficient * capital) if capital is not None else n(coefficient) + "S"
    if not weight:
        return base
    deduction = (
        n(weight * payment)
        if payment is not None
        else (n(weight) if weight != 1 else "") + "x"
    )
    return base + "-" + deduction


def symbolic_schedule(a):
    q, k = a.question, a.factor
    capital = None if q.target == "capital" else a.capital
    payment = None if q.payment is None else a.payment
    rows = []
    weight = 0
    for j in range(1, 4):
        accrued = expression(capital, k**j, payment, weight * k)
        weight = weight * k + 1
        after = expression(capital, k**j, payment, weight)
        rows.append((accrued, after))
    return rows


def table(a):
    q = a.question
    html = "<table><tbody><tr>"
    for title in (
        "Год",
        "Долг в январе, тыс. руб.",
        "Выплата, тыс. руб.",
        "Долг в июле, тыс. руб.",
    ):
        html += (
            '<th data-align="center" data-cell-tone="source-header" data-valign="middle">'
            + title
            + "</th>"
        )
    html += "</tr>"
    rows = [(str(q.year), "", "", inline(n(a.capital)))]
    for j, (accrued, after) in enumerate(symbolic_schedule(a), 1):
        payment = (
            "x" if j < 3 else (n(q.total) + "-2x" if q.total is not None else n(a.last))
        )
        rows.append(
            (
                str(q.year + j),
                inline(accrued),
                inline(payment),
                inline(after if j < 3 else "0"),
            )
        )
    for row in rows:
        html += (
            "<tr>"
            + "".join(
                '<td data-align="center" data-valign="middle">' + cell + "</td>"
                for cell in row
            )
            + "</tr>"
        )
    return html + "</tbody></table>"


def unknown_first(a):
    q, k = a.question, a.factor
    html = (
        "<p>Пусть платежи в "
        + str(q.year + 1)
        + " и "
        + str(q.year + 2)
        + " годах составляют по x тыс. руб. Сначала начисляются проценты, затем вносится платёж:</p>"
    )
    html += factor(a)
    if q.target == "first":
        html += "<p>Заполним таблицу в соответствии с условием задачи:</p>" + table(a)
    else:
        for j, (accrued, after) in enumerate(symbolic_schedule(a), 1):
            html += (
                "<p>В январе "
                + str(q.year + j)
                + " года долг в тысячах рублей равен:</p>"
                + line(accrued)
            )
            if j < 3:
                html += "<p>После очередной выплаты, к июлю, остаётся:</p>" + line(
                    after
                )
    weight = k * k + k
    value = q.total if q.total is not None else a.last
    coefficient = weight - 2 if q.total is not None else weight
    html += "<p>В третьем году последний платёж полностью погашает оставшийся долг. "
    if q.total is not None:
        html += "Так как сумма всех выплат известна, последний платёж равен общей сумме за вычетом первых двух:</p>"
        html += line("P_3=" + n(q.total) + "-2x")
    else:
        html += "Его величина указана в условии:</p>"
    rhs = n(q.total) + "-2x" if q.total is not None else n(a.last)
    html += line(symbolic_schedule(a)[-1][0] + "=" + rhs)
    html += line(n(coefficient) + "x=" + n(a.capital * k**3) + "-" + n(value))
    html += line(n(coefficient) + "x=" + n(a.capital * k**3 - value))
    html += line(
        "x="
        + fraction(n(a.capital * k**3 - value), n(coefficient))
        + "="
        + n(a.payment)
    )
    return html


def known_first(a):
    q, k = a.question, a.factor
    html = (
        "<p>Проследим, как меняется долг: каждый январь на остаток начисляются проценты, затем до июля выплачивается указанная часть долга. Все суммы выразим в тысячах рублей:</p>"
        + factor(a)
    )
    for j in range(1, 4):
        html += "<p>В январе " + str(q.year + j) + " года долг составит:</p>"
        html += line(n(a.debts[j - 1]) + r"\cdot" + n(k) + "=" + n(a.debts[j - 1] * k))
        if j < 3:
            html += "<p>После платежа останется:</p>"
            html += line(
                n(a.debts[j - 1] * k) + "-" + n(a.payment) + "=" + n(a.debts[j])
            )
    html += "<p>Третий платёж равен всему оставшемуся долгу, поэтому кредит будет погашен полностью:</p>"
    return html + line("P_3=" + n(a.last) + r"\text{ тыс. руб.}")


def unknown_capital(a):
    q, k = a.question, a.factor
    html = (
        "<p>Пусть сумма кредита равна S тыс. руб. Запишем долг в январе после начисления процентов и в июле после очередного платежа:</p>"
        + factor(a)
    )
    for j, (accrued, after) in enumerate(symbolic_schedule(a), 1):
        html += "<p>В январе " + str(q.year + j) + " года:</p>" + line(accrued)
        if j < 3:
            html += (
                "<p>После выплаты "
                + n(a.payment)
                + " тыс. руб., к июлю:</p>"
                + line(after)
            )
    weighted = (k * k + k) * a.payment
    html += "<p>Последний платёж должен равняться всему оставшемуся долгу. Получаем уравнение для суммы кредита:</p>"
    html += line(n(k**3) + "S-" + n(weighted) + "=" + n(a.last))
    html += line(
        n(k**3) + "S=" + n(a.last) + "+" + n(weighted) + "=" + n(a.last + weighted)
    )
    return html + line(
        "S="
        + fraction(n(a.last + weighted), n(k**3))
        + "="
        + n(a.capital)
        + r"\text{ тыс. руб.}"
    )


def requested(a):
    q = a.question
    if q.target in {"capital", "last"}:
        return ""
    if q.target == "first":
        return (
            "<p>Переведём найденный первый платёж из тысяч рублей в рубли:</p>"
            + line(n(a.payment) + r"\cdot1000=" + n(a.result) + r"\text{ руб.}")
        )
    html = "<p>Сложим первые два одинаковых платежа и последний платёж:</p>"
    html += line(
        "V=2x+P_3=2\\cdot"
        + n(a.payment)
        + "+"
        + n(a.last)
        + "="
        + n(a.total)
        + r"\text{ тыс. руб.}"
    )
    if q.scale == 1000:
        html += "<p>Выразим общую выплату в рублях:</p>" + line(
            n(a.total) + r"\cdot1000=" + n(a.result) + r"\text{ руб.}"
        )
    return html


def proof(a):
    if a.question.target == "rate":
        from .loan_rate import proof as rate_proof

        return section(rate_proof(a), "Решение")
    if a.question.target == "capital":
        html = unknown_capital(a)
    elif a.question.payment is None:
        html = unknown_first(a)
    else:
        html = known_first(a)
    return section(html + requested(a), "Решение")
