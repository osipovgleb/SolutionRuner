"""The parent's spring/summer speed table and linear-system substitution."""

from html import escape

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .water_balances import seasonal_factors


def inline(formula):
    return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'


def proof(a):
    q, v = a.question, a.question.values
    gap = n(v["gap"])
    spring, summer = v["spring_ratio"], v["summer_ratio"]
    first, second = seasonal_factors(q)
    boat, current = first * a.root, a.root
    html = "<p>Пусть x км/ч — собственная скорость катера, y км/ч — скорость течения весной. Летом течение медленнее. Для движения против течения обе скорости должны быть положительны:</p>"
    html += line("x>y>" + gap)
    html += (
        "<table><tbody><tr><th></th><th>Скорость весной</th><th>Скорость летом</th></tr><tr><td>По течению</td><td>"
        + inline("x+y")
        + "</td><td>"
        + inline("x+y-" + gap)
        + "</td></tr><tr><td>Против течения</td><td>"
        + inline("x-y")
        + "</td><td>"
        + inline("x-y+" + gap)
        + "</td></tr></tbody></table>"
    )
    html += "<p>Отношения скоростей по течению и против течения задают систему уравнений:</p>"
    html += line(
        r"\begin{cases}"
        + frac("x+y", "x-y")
        + "="
        + n(spring)
        + r",\\"
        + frac("x+y-" + gap, "x-y+" + gap)
        + "="
        + n(summer)
        + r".\end{cases}"
    )
    html += (
        "<p>Умножим на положительные знаменатели и соберём коэффициенты при x и y:</p>"
    )
    html += line(
        r"\begin{cases}"
        + n(spring.q)
        + "(x+y)="
        + n(spring.p)
        + r"(x-y),\\"
        + n(summer.q)
        + "(x+y-"
        + gap
        + ")="
        + n(summer.p)
        + "(x-y+"
        + gap
        + r").\end{cases}"
    )
    html += line(
        r"\begin{cases}"
        + n(spring.p - spring.q)
        + "x="
        + n(spring.p + spring.q)
        + r"y,\\"
        + n(summer.p - summer.q)
        + "x="
        + n(summer.p + summer.q)
        + "(y-"
        + gap
        + r").\end{cases}"
    )
    html += "<p>Выразим x из обоих уравнений и приравняем выражения:</p>"
    html += line("x=" + n(first) + "y=" + n(second) + "(y-" + gap + ")")
    html += line(
        n(second - first)
        + "y="
        + n(second * v["gap"])
        + r"\quad\Rightarrow\quad y="
        + n(current)
    )
    html += line("x=" + n(first) + r"\cdot" + n(current) + "=" + n(boat))
    requested = (
        "собственную скорость катера"
        if q.kind == "water_season_boat"
        else "скорость течения весной"
    )
    return (
        html
        + f"<p>Полученные скорости удовлетворяют ограничениям. В условии требуется найти {requested}:</p>"
        + line(("x=" if q.kind == "water_season_boat" else "y=") + n(a.result))
    )
