"""Finite laws and lotteries read from canonical HTML table cells."""

import re
from fractions import Fraction

from .common import UnsupportedCondition, fmt, line, number, result

_LAW = "В таблице показано распределение случайной величины X. Найдите EX — математическое ожидание этой случайной величины."
_VARIANCE = "Найдите дисперсию случайной величины x, если ее распределение вероятностей имеет вид"
_LOTTERY = re.compile(
    r"В таблице показано количество билетов и возможные выигрыши беспроигрышной денежной лотереи\. Цена билета лотереи равна (?P<price>\d+) рублей\. Всего билетов выпущено (?P<n>\d+) штук\. Участник покупает один случайный билет\. На сколько рублей цена билета выше, чем математическое ожидание выигрыша\?"
)
_WINNING = re.compile(
    r"Организаторы лотереи выпустили (?P<n>\d+(?: \d{3})*) билетов\. Выигрыши распределены следующим образом\. Найдите математическое ожидание величины «выигрыш на один билет»\. Ответ дайте в рублях\."
)


def _rows(tables, headers, *, first_header_aliases=()):
    if len(tables) != 1 or len(tables[0]) != 2:
        raise UnsupportedCondition("exactly one two-row distribution table is required")
    a, b = tables[0]
    if (
        len(a) != len(b)
        or len(a) < 3
        or a[0] not in (headers[0], *first_header_aliases)
        or b[0] != headers[1]
    ):
        raise UnsupportedCondition(
            "the distribution table labels or columns are invalid"
        )
    return [number(x) for x in a[1:]], [number(x) for x in b[1:]]


def expectation(values, probabilities):
    if not values or len(values) != len(probabilities):
        raise UnsupportedCondition(
            "each support value requires exactly one probability"
        )
    if any(p < 0 or p > 1 for p in probabilities) or sum(probabilities) != 1:
        raise UnsupportedCondition(
            "distribution probabilities must be nonnegative and sum to one"
        )
    e = sum(x * p for x, p in zip(values, probabilities))
    html = (
        "<p>Математическое ожидание дискретной величины — сумма произведений её возможных значений на их вероятности:</p>"
        + line(r"E(X)=\sum_i x_i p_i")
    )
    html += line(
        "E(X)="
        + "+".join(rf"({fmt(x)})\cdot {fmt(p)}" for x, p in zip(values, probabilities))
    )
    return e, html


def _variance(values, weights):
    ps = [p / 100 for p in weights]
    e, html = expectation(values, ps)
    deviations = [x - e for x in values]
    squares = [x * x for x in deviations]
    html += line("E(X)=" + fmt(e))
    html += "<p>Перейдём к отклонениям от среднего, затем возведём их в квадрат. Вероятности остаются прежними:</p>"
    html += (
        "<table><tbody><tr><td>Значение X−E(X)</td>"
        + "".join(
            '<td><span data-inline-latex="' + fmt(x) + '"></span></td>'
            for x in deviations
        )
        + "</tr><tr><td>Квадрат отклонения</td>"
        + "".join(
            '<td><span data-inline-latex="' + fmt(x) + '"></span></td>' for x in squares
        )
        + "</tr></tbody></table>"
    )
    html += "<p>Дисперсия — математическое ожидание квадрата отклонения:</p>" + line(
        r"D(X)=E((X-E(X))^2)"
    )
    html += line(
        "D(X)=" + "+".join(rf"{fmt(x)}\cdot {fmt(p)}" for x, p in zip(squares, ps))
    )
    return result(sum(x * p for x, p in zip(squares, ps)), html, "D(X)")


def solve(text, tables):
    if text == _LAW:
        xs, ps = _rows(tables, ("Значения X", "Вероятности"))
        e, html = expectation(xs, ps)
        return result(e, html)
    if text == _VARIANCE:
        return _variance(*_rows(tables, ("Значение x", "Вероятность, %")))
    match = _LOTTERY.fullmatch(text) or _WINNING.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported distribution-table question")
    total = int(match["n"].replace(" ", ""))
    all_tickets = "price" in match.re.groupindex
    xs, counts = _rows(
        tables,
        ("Выигрыш", "Количество билетов")
        if all_tickets
        else ("Выигрыш (в рублях)", "Число выигрышных билетов"),
        first_header_aliases=("Выигрыш, руб.",) if all_tickets else (),
    )
    if (
        total <= 0
        or any(c.denominator != 1 or c < 0 for c in counts)
        or sum(counts) > total
        or any(x < 0 for x in xs)
    ):
        raise UnsupportedCondition("invalid lottery counts, prizes or ticket total")
    if all_tickets and sum(counts) != total:
        raise UnsupportedCondition(
            "a guaranteed-prize lottery must account for every ticket"
        )
    ps = [c / total for c in counts]
    if sum(counts) < total:
        xs = [0, *xs]
        ps = [1 - sum(ps), *ps]
    e, html = expectation(xs, ps)
    html = (
        "<p>Вероятность каждого выигрыша равна числу соответствующих билетов, делённому на общее число билетов. Если есть проигрышные билеты, им соответствует нулевой выигрыш.</p>"
        + html
        + line("E(X)=" + fmt(e))
    )
    if all_tickets:
        price = Fraction(int(match["price"]))
        difference = price - e
        if difference < 0:
            raise UnsupportedCondition(
                "the question asserts a ticket price above expected prize"
            )
        html += "<p>Сравним цену билета с ожидаемым выигрышем:</p>" + line(
            rf"\Delta={fmt(price)}-{fmt(e)}"
        )
        html += "<p>При неизменных условиях это средняя потеря на билет в длительной серии игр.</p>"
        return result(difference, html, r"\Delta")
    html += "<p>Математическое ожидание описывает средний выигрыш на один билет в длительной серии при тех же условиях.</p>"
    return result(e, html)
