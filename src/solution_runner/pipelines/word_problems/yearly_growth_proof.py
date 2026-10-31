"""Parent geometric-growth calculation and its profit-versus-capital notes."""

from html import escape

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n


def factor(a, symbol):
    return line(symbol + "=1+" + frac(n(a.rate), "100") + "=" + n(a.factor))


def power(a, symbol):
    return line(
        symbol
        + "="
        + n(a.capital)
        + r"\cdot("
        + n(a.factor)
        + ")^{"
        + str(a.end)
        + "-"
        + str(a.start)
        + "}="
        + n(a.capital)
        + r"\cdot("
        + n(a.factor)
        + ")^{"
        + str(a.periods)
        + "}"
    ) + line(
        symbol
        + "="
        + n(a.capital)
        + r"\cdot("
        + n(a.factor**a.periods)
        + ")="
        + n(a.result)
    )


def profit(a):
    html = f"<p>Прибыль, которую получает {escape(a.name)}, каждый год увеличивается на указанный процент по сравнению с предыдущим годом. Найдём, какую долю прежней прибыли составляет новая прибыль, и запишем знаменатель геометрической прогрессии:</p>"
    html += line(r"100\%+" + n(a.rate) + r"\%=" + n(100 + a.rate) + r"\%")
    html += factor(a, "q")
    html += "<p>Начальная прибыль — первый член прогрессии. Число ежегодных увеличений равно разности требуемого и начального годов:</p>"
    html += line("k=" + str(a.end) + "-" + str(a.start) + "=" + str(a.periods))
    html += line("b_{k+1}=b_1q^k")
    html += power(a, "b_{" + str(a.periods + 1) + "}")
    html += "<p><b>Примечание.</b> Прибыли можно также найти последовательно, каждый раз умножая прибыль предыдущего года на тот же множитель:</p>"
    value = a.capital
    for year in range(a.start + 1, a.end + 1):
        next_value = value * a.factor
        html += line(
            "b_{"
            + str(year - a.start + 1)
            + "}="
            + n(value)
            + r"\cdot("
            + n(a.factor)
            + ")="
            + n(next_value)
            + r"\quad("
            + str(year)
            + r"\text{ год})"
        )
        value = next_value
    return (
        html
        + "<p><b>Примечание.</b> В задаче речь идёт о прибыли за указанный год, то есть о сумме, заработанной за год. Это не капитал на конец года. Поэтому из прибыли текущего года не нужно вычитать прибыль предыдущего года.</p>"
    )


def companies(a):
    html = ""
    for i, account in enumerate(a.accounts, 1):
        name = escape(account.name)
        html += f"<p>Прибыль компании «{name}» составляет указанный процент от капитала предыдущего года и остаётся в обороте. Прибавим прибыль к прежнему капиталу и найдём ежегодный множитель:</p>"
        html += line(
            r"100\%+" + n(account.rate) + r"\%=" + n(100 + account.rate) + r"\%"
        )
        html += factor(account, "q_" + str(i))
        html += f"<p>К концу {account.end} года для компании «{name}» произошло {account.periods} ежегодных увеличений капитала:</p>"
        html += power(account, "S_" + str(i))
    first, second = a.accounts
    larger, smaller = sorted((first, second), key=lambda x: x.result, reverse=True)
    html += f"<p>Капитал компании «{escape(larger.name)}» больше. Найдём разность:</p>"
    return html + line(
        r"\Delta S=" + n(larger.result) + "-" + n(smaller.result) + "=" + n(a.result)
    )


def proof(a):
    return profit(a.accounts[0]) if a.kind == "profit" else companies(a)
