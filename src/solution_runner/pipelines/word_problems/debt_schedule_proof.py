"""Keep the parents' debt tables, payment comparisons and interest calculation."""

from html import escape

from ..probability.common import line
from .math_common import fraction
from .math_common import number as n
from .motion_chase_proof import section
from .water_season_proof import inline

REL = {"меньше": r"<", "не больше": r"\leq", "больше": r">", "не меньше": r"\geq"}


def multiple(value):
    return "S" if value == 1 else ("0" if value == 0 else n(value) + "S")


def table(rows, headers):
    html = "<table><tbody><tr>"
    for title in headers:
        html += (
            '<th data-align="center" data-cell-tone="source-header" data-valign="middle">'
            + escape(title)
            + "</th>"
        )
    html += "</tr>"
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


def yearly_table(a):
    q = a.question
    rows = [(str(q.year), "", "", inline("S"))]
    for j, (before, after, payment) in enumerate(
        zip(q.ratios, q.ratios[1:], a.payments), 1
    ):
        payment_formula = multiple(payment)
        if q.kind == "geometric":
            payment_formula = (
                multiple(q.rate / 100 * before)
                + "+"
                + multiple(before - after)
                + "="
                + multiple(payment)
            )
        rows.append(
            (
                str(q.year + j),
                inline(multiple(a.factor * before)),
                inline(payment_formula),
                inline(multiple(after)),
            )
        )
    return table(
        rows,
        (
            "Год",
            "Долг после начисления процентов, " + q.unit,
            "Выплата, " + q.unit,
            "Остаток долга в июле, " + q.unit,
        ),
    )


def payment_lines(a):
    q = a.question
    html = (
        "<p>Когда банк начисляет проценты на июльский остаток, долг умножается на годовой коэффициент. Затем платёж уменьшает его до следующего остатка. Все суммы выражены в "
        + ("тысячах" if q.unit == "тыс. руб." else "миллионах")
        + " рублей:</p>"
    )
    html += line(r"k=1+\frac{" + n(q.rate) + "}{100}=" + n(a.factor))
    for j, (before, after, payment) in enumerate(
        zip(q.ratios, q.ratios[1:], a.payments), 1
    ):
        html += line(
            "P_"
            + str(j)
            + "="
            + n(a.factor)
            + r"\cdot"
            + multiple(before)
            + "-"
            + multiple(after)
            + "="
            + multiple(payment)
        )
    return html


def bound(a):
    q = a.question
    if q.scope == "каждая из выплат" and q.unit == "тыс. руб.":
        html = payment_lines(a)
    else:
        html = "<p>В соответствии с условием задачи заполним таблицу. Каждый платёж равен долгу после начисления процентов за вычетом следующего июльского остатка:</p>"
        html += line(
            r"k=1+\frac{" + n(q.rate) + "}{100}=" + n(a.factor)
        ) + yearly_table(a)
    if q.scope == "каждая из выплат":
        extreme = "наибольшую" if q.extreme == "наибольшее" else "наименьшую"
        html += (
            "<p>Чтобы ограничение выполнялось для каждой выплаты, достаточно проверить "
            + extreme
            + " из них:</p>"
        )
        html += line(
            ("P_{\\max}" if q.extreme == "наибольшее" else "P_{\\min}")
            + "="
            + multiple(a.coefficient)
        )
    else:
        html += "<p>Найдём общую сумму выплат:</p>"
        html += line(
            "V=" + "+".join(multiple(p) for p in a.payments) + "=" + multiple(a.total)
        )
    relation = REL[q.bound]
    boundary = q.limit / a.coefficient
    html += (
        "<p>Запишем требуемое ограничение и разделим на положительный коэффициент:</p>"
    )
    html += line(multiple(a.coefficient) + relation + n(q.limit))
    html += line("S" + relation + fraction(n(q.limit), n(a.coefficient)))
    html += line("S" + relation + n(boundary))
    html += (
        "<p>Выбираем "
        + q.extreme
        + " положительное целое S, удовлетворяющее этому неравенству:</p>"
    )
    return html + line("S=" + n(a.result))


def monthly(a):
    q = a.question
    html = "<p>Не снижая общности рассуждений, примем начальную сумму кредита за 100 руб. Проценты начисляются в конце месяца, а выплаты производятся в первой половине следующего. Будем считать, что выплаты сделаны 14-го числа, перед указанными в таблице датами:</p>"
    html += line(r"k=1+\frac{" + n(q.rate) + "}{100}=" + n(a.factor))
    html += "<p>Обозначим остаток после j-й выплаты через Bⱼ. Выплата равна начисленному долгу за вычетом следующего остатка:</p>"
    html += line(r"P_j=kB_{j-1}-B_j,\qquad B_0=100,\quad B_6=0")
    values = [
        ("Долг, руб.", *[inline(n(100 * a.factor * r)) for r in q.ratios[:-1]]),
        ("Выплата, руб.", *[inline(n(100 * p)) for p in a.payments]),
        (
            "Остаток долга на день выплаты, руб.",
            *[inline(n(100 * r)) for r in q.ratios[1:]],
        ),
        (
            "Остаток долга на день выплаты, %",
            *[inline(n(100 * r) + r"\%") for r in q.ratios[1:]],
        ),
    ]
    html += table(
        values, ("Дата", *["14." + str(month).zfill(2) for month in range(2, 8)])
    )
    html += "<p>Сложим все выплаты и найдём переплату по сравнению с исходными 100 рублями:</p>"
    html += line(
        "V=" + "+".join(n(100 * p) for p in a.payments) + "=" + n(100 * a.total)
    )
    html += line(r"V-S=" + n(100 * a.total) + "-100=" + n(a.result))
    html += line(
        r"\frac{V-S}{S}\cdot100\%="
        + fraction(n(a.result), "100")
        + r"\cdot100\%="
        + n(a.result)
        + r"\%"
    )
    return html


def geometric(a):
    q = a.question
    ratio = q.ratios[1]
    decrease = 100 * (1 - ratio)
    html = "<p>Так как в промежуточные годы долг каждый июль уменьшается на указанный процент, он составляет одну и ту же долю от предыдущего июльского остатка. Составим график погашения долга:</p>"
    html += line(r"d=1-\frac{" + n(decrease) + "}{100}=" + n(ratio))
    html += line(
        r"B_j=S d^j\quad(0\leq j<"
        + str(len(q.ratios) - 1)
        + r"),\qquad B_"
        + str(len(q.ratios) - 1)
        + "=0"
    )
    html += yearly_table(a)
    html += "<p>Сумма всех выплат известна. Сложим платежи из таблицы и найдём первоначальную сумму кредита:</p>"
    html += line(
        "V=" + "+".join(multiple(p) for p in a.payments) + "=" + multiple(a.total)
    )
    html += line(multiple(a.total) + "=" + n(q.limit))
    html += line("S=" + fraction(n(q.limit), n(a.total)))
    return html + line("S=" + n(a.result))


def proof(a):
    return section(
        {"bound": bound, "monthly": monthly, "geometric": geometric}[a.question.kind](
            a
        ),
        "Решение",
    )
