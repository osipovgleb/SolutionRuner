"""Parent root verification and monotonic uniqueness for joint filling times."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_proof import quadratic_steps


def proof(a):
    q, v = a.question, a.question.values
    symbol, difference, joint = q.symbol, n(v["gap"]), n(v["joint"])
    if q.kind == "work_gap_filter":
        html = "<p>Пусть первый фильтр очищает цистерну за t минут, тогда второй — на указанное время быстрее:</p>"
        other = symbol + "-" + difference
        other_time = a.root - v["gap"]
        html += line("t_2=" + other) + line(symbol + ">" + difference)
    else:
        if q.kind == "work_gap_printer":
            html = f"<p>Пусть первый принтер расходует пачку бумаги за {symbol} минут, тогда второму принтеру требуется больше времени:</p>"
        else:
            html = f"<p>Пусть вторая труба наполняет резервуар за {symbol} минут, тогда первой трубе требуется больше времени:</p>"
        other = symbol + "+" + difference
        other_time = a.root + v["gap"]
        html += line(other) + line(symbol + ">0")
    html += "<p>Объём работы примем за 1. За минуту участники вместе выполняют долю, равную сумме их производительностей:</p>"
    html += line(frac("1", symbol) + "+" + frac("1", other) + "=" + frac("1", joint))
    html += "<p>Подбором находим положительное решение. Проверим его подстановкой:</p>"
    html += line(symbol + "=" + n(a.root))
    html += line(
        frac("1", n(a.root)) + "+" + frac("1", n(other_time)) + "=" + frac("1", joint)
    )
    html += "<p>В допустимой области оба знаменателя положительны. Левая часть уравнения строго убывает, поэтому найденное решение единственно:</p>"
    html += line(
        "f'("
        + symbol
        + ")=-"
        + frac("1", symbol + "^2")
        + "-"
        + frac("1", "(" + other + ")^2")
        + "<0"
    )
    if q.kind == "work_gap_filter":
        html += "<p>В условии спрашивается время второго фильтра:</p>" + line(
            "t_2=" + n(a.root) + "-" + difference + "=" + n(a.result)
        )
    if q.kind == "work_gap_printer":
        html += "<p><b>Примечание Михаила Бабинчука.</b> Уравнение можно решить алгебраически. При положительном t умножим на общий знаменатель и решим квадратное уравнение:</p>"
        html += quadratic_steps(a, quantities="времени и производительностей")
    return html
