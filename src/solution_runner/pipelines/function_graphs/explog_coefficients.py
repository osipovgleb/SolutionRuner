"""Parent systems, domain reading and the second range method for graph bases."""

import sympy as sp

from ..probability.common import line
from ..word_problems.math_common import number
from .explog_models import A, exact_log


def n(value):
    return number(value) if value.is_Rational else sp.latex(value)


def power(base, exponent):
    b = n(base) if base.is_Integer else r"\left(" + n(base) + r"\right)"
    return b + "^{" + str(exponent) + "}"


def logarithm(base, argument):
    return r"\log_{" + n(base) + r"}\left(" + str(argument) + r"\right)"


def formula(a, argument="x"):
    model, b = a.question.model, a.shift
    shifted = (
        sp.latex(sp.Symbol(argument) + b)
        if argument == "x"
        else str(argument) + "+(" + n(b) + ")"
    )
    if model == "exp_horizontal":
        return power(a.base, shifted)
    if model.startswith("exp"):
        return power(a.base, argument) + (("+" if b > 0 else "") + n(b) if b else "")
    if model == "log_horizontal":
        return logarithm(a.base, shifted)
    return (n(b) + "+" if b else "") + logarithm(a.base, argument)


def system(rows):
    return line(r"\begin{cases}" + r"\\".join(rows) + r".\end{cases}")


def coordinates(a):
    return (
        "<p>По рисунку определяем значения функции в двух точках. Подставим их координаты в заданную формулу и найдём параметры:</p>"
        + line(r",\qquad ".join("f(" + n(x) + ")=" + n(y) for x, y in a.points))
    )


def base_roots(a):
    equation = a.equation
    html = line(sp.latex(equation) + "=0")
    factored = sp.factor(equation)
    if factored != equation:
        html += line(sp.latex(factored) + "=0")
    for factor, _ in sp.factor_list(equation, A)[1]:
        p = sp.Poly(factor, A)
        if p.degree() == 2:
            aa, bb, cc = p.all_coeffs()
            d = bb**2 - 4 * aa * cc
            if d < 0:
                html += line(
                    "D=("
                    + n(bb)
                    + ")^2-4\\cdot("
                    + n(aa)
                    + r")\cdot("
                    + n(cc)
                    + ")="
                    + n(d)
                    + "<0"
                )
    roots = sp.real_roots(sp.Poly(equation, A))
    html += line(
        r"a\in\left\{" + ";".join(n(r) for r in sorted(set(roots))) + r"\right\}"
    )
    return (
        html
        + "<p>Для показательной или логарифмической функции основание положительно и не равно единице. Поэтому оставляем допустимый корень:</p>"
        + line(r"a>0,\quad a\ne1,\quad a=" + n(a.base))
    )


def logarithmic_vertical(a):
    (x1, y1), (x2, y2) = a.points
    html = coordinates(a) + system(
        [n(y) + "=b+" + logarithm(A, n(x)) for x, y in a.points]
    )
    if x1 == 1:
        html += line(r"\log_a1=0,\qquad b=" + n(y1))
        x, y = x2, y2
    else:
        ratio = exact_log(x2, x1)
        html += "<p>Используем свойство логарифма степени и исключим логарифм из системы:</p>"
        html += line(logarithm(A, n(x2)) + "=" + n(ratio) + logarithm(A, n(x1)))
        html += line(
            "("
            + n(y2)
            + ")-("
            + n(ratio)
            + r")\cdot("
            + n(y1)
            + ")=(1-("
            + n(ratio)
            + r"))b,\qquad b="
            + n(a.shift)
        )
        x, y = x1, y1
    exponent = y - a.shift
    html += line(
        logarithm(A, n(x)) + "=" + n(y) + "-(" + n(a.shift) + ")=" + n(exponent)
    )
    html += line(
        power(A, n(exponent))
        + "="
        + n(x)
        + r",\qquad a>0,\ a\ne1\ \Longrightarrow\ a="
        + n(a.base)
    )
    return html


def logarithmic_domain(a):
    boundary = -a.shift
    html = "<p>Область определения функции — интервал (−b; +∞). По рисунку определяем вертикальную асимптоту и границу области определения:</p>"
    html += line(
        r"D(f)=(-b;+\infty)=(" + n(boundary) + r";+\infty),\qquad b=" + n(a.shift)
    )
    x, y = next((p for p in a.points if p[1] == 2), a.points[0])
    html += "<p>Учитывая координаты точки графика, найдём основание:</p>"
    html += line(
        "f("
        + n(x)
        + ")="
        + n(y)
        + r",\qquad"
        + logarithm(A, n(x) + "+(" + n(a.shift) + ")")
        + "="
        + n(y)
    )
    html += line(power(A, n(y)) + "=" + n(x + a.shift))
    return html + line(r"a>0,\quad a\ne1\quad\Longrightarrow\quad a=" + n(a.base))


def logarithmic_system(a):
    (x1, y1), (x2, y2) = a.points
    html = coordinates(a) + system(
        [logarithm(A, n(x) + "+b") + "=" + n(y) for x, y in a.points]
    )
    html += system([n(x) + "+b=" + power(A, n(y)) for x, y in a.points])
    html += "<p>Вычтем первое равенство из второго, чтобы исключить b:</p>"
    html += line(power(A, n(y2)) + "-" + power(A, n(y1)) + "=" + n(x2 - x1))
    html += base_roots(a)
    return html + line("b=" + power(a.base, n(y1)) + "-(" + n(x1) + ")=" + n(a.shift))


def exponential_system(a):
    (x1, y1), (x2, y2) = a.points
    html = coordinates(a) + system([power(A, n(x)) + "+b=" + n(y) for x, y in a.points])
    html += "<p>Вычтем первое уравнение из второго, чтобы исключить b:</p>"
    html += line(power(A, n(x2)) + "-" + power(A, n(x1)) + "=" + n(y2 - y1))
    if min(x1, x2) < 0:
        html += "<p>Основание положительно, поэтому умножение уравнения на его степень сохраняет корни:</p>"
    html += base_roots(a)
    return html + line("b=" + n(y1) + "-(" + power(a.base, n(x1)) + ")=" + n(a.shift))


def exponential_horizontal(a):
    html = coordinates(a) + system(
        [n(y) + "=" + power(A, n(x) + "+b") for x, y in a.points]
    )
    x, _y = next(p for p in a.points if p[1] == 1)
    other = next(p for p in a.points if p[0] != x)
    html += "<p>При допустимом основании степень равна единице только при нулевом показателе. Найдём сдвиг, затем основание:</p>"
    html += line(r"a>0,\quad a\ne1,\quad" + n(x) + r"+b=0,\quad b=" + n(a.shift))
    xx, yy = other
    html += line(power(A, n(xx) + "+(" + n(a.shift) + ")") + "=" + n(yy))
    return html + line(
        power(A, n(xx + a.shift)) + "=" + n(yy) + r",\qquad a=" + n(a.base)
    )


def plain(a):
    x, y = a.points[0]
    html = "<p>По графику находим значение функции в отмеченной точке и определяем основание:</p>"
    html += line("f(" + n(x) + ")=" + n(y))
    raw = (
        power(A, n(x)) + "=" + n(y)
        if a.question.model == "exp_plain"
        else logarithm(A, n(x)) + "=" + n(y)
    )
    html += line(raw)
    return html + line(r"a>0,\quad a\ne1\quad\Longrightarrow\quad a=" + n(a.base))


def exponential_range(a):
    html = "<p>Множество значений функции — интервал (b; +∞). По рисунку определяем горизонтальную асимптоту и границу множества значений:</p>"
    html += line(r"E(f)=(" + n(a.shift) + r";+\infty),\qquad b=" + n(a.shift))
    x, y = next(p for p in a.points if p[0] != 0)
    html += (
        "<p>Подставим координаты точки графика и найдём положительное основание:</p>"
    )
    html += line(power(A, n(x)) + "+(" + n(a.shift) + ")=" + n(y))
    html += line(
        power(A, n(x))
        + "="
        + n(y - a.shift)
        + r",\qquad a>0,\ a\ne1\ \Longrightarrow\ a="
        + n(a.base)
    )
    xx, yy = next(p for p in a.points if p[0] != x)
    html += "<p>Проверим формулу по второй точке:</p>"
    return html + line("f(" + n(xx) + ")=" + formula(a, n(xx)) + "=" + n(yy))


def coefficients(a):
    readers = {
        "log_vertical": logarithmic_vertical,
        "log_horizontal": logarithmic_domain
        if a.question.mode == "value"
        else logarithmic_system,
        "exp_vertical": exponential_system,
        "exp_horizontal": exponential_horizontal,
        "exp_plain": plain,
        "log_plain": plain,
    }
    return readers[a.question.model](a)
