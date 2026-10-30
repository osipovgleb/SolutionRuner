"""Geometric area and differentiable gluing of a piecewise primitive."""

import sympy as sp

from ..probability.common import line
from .common import X
from .graph_integral_proof import difference_name, latex, number


def cases(left, right, join):
    return (
        r"\begin{cases}"
        + (left if isinstance(left, str) else latex(left))
        + r",&x<"
        + number(join)
        + r",\\"
        + (right if isinstance(right, str) else latex(right))
        + r",&x\geq"
        + number(join)
        + r".\end{cases}"
    )


def piecewise_geometry(m, operation):
    a, b, h, c = m.lower, m.upper, m.height, m.join
    result = number(m.result)
    if operation == "integral":
        html = "<p>Определённый интеграл неотрицательной функции равен площади под её графиком на заданном отрезке. Разобьём область на прямоугольный треугольник и прямоугольник:</p>"
        triangle = sp.simplify((b - c) * h / 2)
        rectangle = sp.simplify((c - a) * h)
        html += line(
            r"S_{\mathrm{тр}}=\frac12\cdot("
            + number(b)
            + "-"
            + number(c)
            + ")\\cdot"
            + number(h)
            + "="
            + number(triangle)
        )
        html += line(
            r"S_{\mathrm{пр}}=("
            + number(c)
            + "-"
            + number(a)
            + ")\\cdot"
            + number(h)
            + "="
            + number(rectangle)
        )
        html += "<p>Сумма площадей даёт искомый интеграл:</p>" + line(
            r"\int_{"
            + number(a)
            + "}^{"
            + number(b)
            + r"}f(x)\,dx="
            + number(triangle)
            + "+"
            + number(rectangle)
            + "="
            + result
        )
        return html
    html = "<p>Разность значений первообразной равна площади выделенной на рисунке трапеции:</p>"
    html += line(r"F(b)-F(a)=\int_a^b f(x)\,dx=S")
    html += "<p>Длины параллельных оснований и высота трапеции:</p>"
    html += line("B_1=" + number(c) + "-" + number(a) + "=" + number(c - a))
    html += line("B_2=" + number(b) + "-" + number(a) + "=" + number(b - a))
    html += line("h=" + number(h))
    html += line(
        difference_name(m)
        + r"=\frac{"
        + number(c - a)
        + "+"
        + number(b - a)
        + r"}{2}\cdot"
        + number(h)
        + "="
        + result
    )
    return html


def piecewise(m, operation):
    html = piecewise_geometry(m, operation)
    if operation == "integral":
        return html
    c, h = m.join, m.height
    C1 = sp.Symbol("C_1")
    left = h * X + C1
    joined = m.right_primitive + C1 + m.adjustment
    html += "<p><b>Аналитическое решение.</b> Запишем функцию по графику и найдём первообразную на каждой из частей:</p>"
    html += line("f(x)=" + cases(h, m.right, c))
    html += line(
        "F(x)=" + cases(latex(h * X) + "+C_1", latex(m.right_primitive) + "+C_2", c)
    )
    html += "<p>Первообразная дифференцируема, а значит, непрерывна в каждой точке своей области определения. В точке соединения выражения должны совпасть:</p>"
    html += line("x=" + number(c))
    html += line(
        number(h * c) + "+C_1=" + number(m.right_primitive.subs(X, c)) + "+C_2"
    )
    html += line("C_2=" + latex(C1 + m.adjustment))
    html += line(
        "F(x)="
        + cases(
            latex(h * X) + "+C_1", latex(m.right_primitive + m.adjustment) + "+C_1", c
        )
    )
    html += "<p>Непрерывности недостаточно: проверим дифференцируемость в точке соединения. Найдём односторонние производные по определению:</p>"
    html += line(
        r"F'_-("
        + number(c)
        + r")=\lim_{x\to "
        + number(c)
        + r"-0}\frac{F(x)-F("
        + number(c)
        + r")}{x-"
        + number(c)
        + r"}"
    )
    html += line(
        r"=\lim_{x\to "
        + number(c)
        + r"-0}\frac{"
        + number(h)
        + "(x-"
        + number(c)
        + r")}{x-"
        + number(c)
        + "}="
        + number(h)
    )
    quotient = h + m.slope * (X - c) / 2
    html += line(
        r"F'_+("
        + number(c)
        + r")=\lim_{x\to "
        + number(c)
        + r"+0}\frac{F(x)-F("
        + number(c)
        + r")}{x-"
        + number(c)
        + r"}"
    )
    html += line(
        r"=\lim_{x\to "
        + number(c)
        + r"+0}\left("
        + latex(quotient)
        + r"\right)="
        + number(h)
    )
    html += "<p>Односторонние производные равны значению функции. Следовательно, найденная непрерывная функция является первообразной и в точке соединения:</p>"
    html += line("F'(" + number(c) + ")=f(" + number(c) + ")=" + number(h))
    html += "<p>Вычислим требуемую разность; общая константа сокращается:</p>"
    html += line(
        difference_name(m)
        + "=("
        + number(m.right_primitive.subs(X, m.upper) + m.adjustment)
        + "+C_1)-("
        + number(h * m.lower)
        + "+C_1)="
        + number(m.result)
    )
    return html + piecewise_note(m, left, joined)


def piecewise_note(m, left, joined):
    html = "<p><b>Примечание.</b> Линейная и квадратичная ветви графика первообразной имеют в точке соединения общую касательную. Их разность:</p>"
    html += line(
        "("
        + latex(joined)
        + ")-("
        + latex(left)
        + ")="
        + latex(m.slope / 2)
        + "(x-"
        + number(m.join)
        + ")^2"
    )
    html += "<p>Она обращается в нуль только в точке соединения; там же совпадают производные обеих ветвей. Проверять только непрерывность при склейке первообразной было бы недостаточно.</p>"
    return html
