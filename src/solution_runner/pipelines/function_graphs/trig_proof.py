"""Keep the parent's zero-value method, signed coefficient and periodic reduction."""

import sympy as sp

from ..probability.common import line
from ..word_problems.math_common import number as n
from ..word_problems.motion_chase_proof import section
from .trig_graph import FUNCTIONS


def trig(function, argument):
    name = r"\tan" if function == "tan" else "\\" + function
    return name + r"\left(" + sp.latex(argument) + r"\right)"


def proof(a):
    q = a.question
    function = FUNCTIONS[q.function]
    x0, y0 = a.zero
    x1, y1 = a.probe
    html = "<p>По шкалам рисунка одна клетка по оси x соответствует π/4, а по оси y — 1/2. По графику определим значение функции в точке, где тригонометрический множитель равен нулю:</p>"
    html += line("f(" + sp.latex(x0) + ")=" + n(y0))
    html += line(trig(q.function, x0) + "=0")
    html += line("a" + trig(q.function, x0) + "+b=" + n(y0))
    html += line(r"a\cdot0+b=" + n(y0) + r",\qquad b=" + n(a.shift))
    if q.kind == "b":
        return section(html, "Решение")
    html += "<p>Далее подставим координаты ещё одной точки графика, чтобы найти коэффициент a:</p>"
    html += line("f(" + sp.latex(x1) + ")=" + n(y1))
    html += line(trig(q.function, x1) + "=" + n(function(x1)))
    html += line("a" + trig(q.function, x1) + "+(" + n(a.shift) + ")=" + n(y1))
    html += line(
        "a\\cdot("
        + n(function(x1))
        + ")="
        + n(y1)
        + "-("
        + n(a.shift)
        + ")="
        + n(y1 - a.shift)
    )
    html += line(
        "a="
        + r"\frac{"
        + n(y1 - a.shift)
        + "}{"
        + n(function(x1))
        + "}="
        + n(a.coefficient)
    )
    if q.kind == "a":
        return section(html, "Решение")
    html += "<p>Искомая функция имеет вид:</p>"
    html += line(
        "y=("
        + n(a.coefficient)
        + ")"
        + trig(q.function, sp.Symbol("x"))
        + "+("
        + n(a.shift)
        + ")"
    )
    target = q.target
    reduced = (target / sp.pi % 2) * sp.pi
    periods = sp.simplify((target - reduced) / (2 * sp.pi))
    html += "<p>Найдём значение при заданном аргументе. Используем период 2π и табличное значение тригонометрической функции:</p>"
    html += line(
        sp.latex(target) + "=" + sp.latex(2 * periods * sp.pi) + "+" + sp.latex(reduced)
    )
    html += line(
        trig(q.function, target)
        + "="
        + trig(q.function, reduced)
        + "="
        + n(function(reduced))
    )
    html += line(
        "y("
        + sp.latex(target)
        + ")=("
        + n(a.coefficient)
        + r")\cdot("
        + n(function(reduced))
        + ")+("
        + n(a.shift)
        + ")="
        + n(a.result)
    )
    return section(html, "Решение")
