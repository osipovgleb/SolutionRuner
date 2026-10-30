"""Parent-style geometric, analytic and translated-area explanations."""

import sympy as sp

from ..probability.common import line
from .common import T, X


def latex(expression):
    return sp.latex(expression)


def number(value):
    return latex(sp.Rational(value))


def difference_name(model):
    return "F(" + number(model.upper) + ")-F(" + number(model.lower) + ")"


def substitution(poly, value, powers=True):
    p = sp.Poly(poly, X)
    terms = []
    for degree in range(p.degree(), -1, -1):
        coefficient = p.nth(degree)
        if not coefficient:
            continue
        if degree:
            power = (
                sp.Pow(value, degree, evaluate=False)
                if powers and degree != 1
                else value**degree
            )
            terms.append(
                (
                    sp.Mul(coefficient, power, evaluate=False)
                    if coefficient != 1
                    else power
                )
                if powers
                else coefficient * power
            )
        else:
            terms.append(coefficient)
    return sp.latex(sp.Add(*terms, evaluate=False), order="none")


def endpoint_values(m):
    html = "<p>Площадь выделенной фигуры равна разности значений данной первообразной на границах:</p>"
    html += line("S=" + difference_name(m))
    for value in [m.upper, m.lower]:
        html += line("F(" + number(value) + ")=" + substitution(m.primitive, value))
        html += line("=" + substitution(m.primitive, value, False))
        html += line("=" + number(m.primitive.subs(X, value)))
    html += line(
        "S="
        + number(m.primitive.subs(X, m.upper))
        + "-("
        + number(m.primitive.subs(X, m.lower))
        + ")="
        + number(m.result)
    )
    return html


def complete_cube(m):
    coefficient = sp.Poly(m.primitive, X).nth(3)
    remainder = sp.expand(
        m.primitive - coefficient * (X - m.center) ** 3 - m.vertex_height * X
    )
    form = sp.Add(
        coefficient * sp.Pow(X - m.center, 3, evaluate=False),
        m.vertex_height * X,
        remainder,
        evaluate=False,
    )
    html = "<p><b>Приведём другое решение.</b> Вычисления можно упростить, выделив полный куб:</p>"
    html += line("F(x)=" + latex(m.primitive))
    html += line("=" + latex(form))
    html += "<p>Постоянное слагаемое в разности сокращается:</p>"
    html += line(
        difference_name(m)
        + "="
        + number(coefficient)
        + r"\left[("
        + number(m.upper)
        + "-("
        + number(m.center)
        + "))^3-("
        + number(m.lower)
        + "-("
        + number(m.center)
        + r"))^3\right]+"
        + number(m.vertex_height)
        + "("
        + number(m.upper)
        + "-("
        + number(m.lower)
        + "))"
    )
    radius = (m.upper - m.lower) / 2
    html += line(
        "="
        + number(coefficient)
        + "("
        + number(radius)
        + "^3-("
        + number(-radius)
        + ")^3)+"
        + number(m.vertex_height)
        + r"\cdot"
        + number(m.upper - m.lower)
    )
    html += line("=" + number(m.result))
    return html


def factor_differences(m):
    p = sp.Poly(m.primitive, X)
    a, b = m.lower, m.upper
    A, B, C = [p.nth(i) for i in [3, 2, 1]]
    html = "<p><b>Приведём ещё одно решение.</b> Используем формулы сокращённого умножения. Для кубического многочлена:</p>"
    html += line(r"F(x)=Ax^3+Bx^2+Cx+D")
    html += line("A=" + number(A) + ",\\quad B=" + number(B) + ",\\quad C=" + number(C))
    html += line(r"F(b)-F(a)=A(b^3-a^3)+B(b^2-a^2)+C(b-a)")
    html += line(r"=(b-a)\left[A(b^2+ab+a^2)+B(b+a)+C\right]")
    first, second, third = A * (b * b + a * b + a * a), B * (b + a), C
    html += "<p>Подставим границы и упростим каждое слагаемое в скобках:</p>"
    html += line(
        difference_name(m)
        + "=("
        + number(b)
        + "-("
        + number(a)
        + r"))\left["
        + number(A)
        + "(("
        + number(b)
        + ")^2+("
        + number(a)
        + ")("
        + number(b)
        + ")+("
        + number(a)
        + ")^2)+("
        + number(B)
        + ")("
        + number(b)
        + "+("
        + number(a)
        + "))+"
        + number(C)
        + r"\right]"
    )
    html += line(
        "="
        + number(b - a)
        + r"\left["
        + number(first)
        + "+("
        + number(second)
        + ")+"
        + number(third)
        + r"\right]"
    )
    html += line(
        "="
        + number(b - a)
        + r"\cdot"
        + number(first + second + third)
        + "="
        + number(m.result)
    )
    return html


def translated_direct(m, shifted, primitive, radius):
    lower, upper = number(-radius), number(radius)
    html = line(
        r"S=\int_{"
        + lower
        + "}^{"
        + upper
        + r"}\left("
        + latex(shifted)
        + r"\right)\,dt=\left["
        + latex(primitive)
        + r"\right]_{"
        + lower
        + "}^{"
        + upper
        + "}"
    )
    return html + line(
        "="
        + number(primitive.subs(T, radius))
        + "-("
        + number(primitive.subs(T, -radius))
        + ")="
        + number(m.result)
    )


def translated_area(m, full_methods):
    shifted = m.curvature * T**2 + m.vertex_height
    primitive = m.curvature * T**3 / 3 + m.vertex_height * T
    radius = (m.upper - m.lower) / 2
    square = sp.Add(
        m.curvature * sp.Pow(X - m.center, 2, evaluate=False),
        m.vertex_height,
        evaluate=False,
    )
    html = "<p>Найдём формулу функции, график которой изображён на рисунке:</p>"
    html += line("f(x)=F'(x)=" + latex(m.function))
    html += line("=" + latex(square))
    html += "<p>Сдвиг вдоль оси абсцисс не меняет площадь. Перенесём начало отсчёта в вершину параболы:</p>"
    html += line("t=x-(" + number(m.center) + ")")
    html += line(
        "x\\in["
        + number(m.lower)
        + ";"
        + number(m.upper)
        + r"]\quad\Longrightarrow\quad t\in["
        + number(-radius)
        + ";"
        + number(radius)
        + "]"
    )
    if full_methods:
        html += translated_direct(m, shifted, primitive, radius)
        html += "<p><b>Примечание.</b> Вычисление можно упростить: подынтегральная функция чётная, поэтому обе половины фигуры имеют равные площади.</p>"
    else:
        html += "<p>Полученная функция чётная, поэтому достаточно удвоить площадь правой половины:</p>"
    html += line(
        "S="
        + r"\int_{"
        + number(-radius)
        + "}^{"
        + number(radius)
        + r"}\left("
        + latex(shifted)
        + r"\right)\,dt=2\int_0^{"
        + number(radius)
        + r"}\left("
        + latex(shifted)
        + r"\right)\,dt"
    )
    html += line(r"=2\left[" + latex(primitive) + r"\right]_0^{" + number(radius) + "}")
    html += line(
        "=2\\left("
        + number(m.curvature / 3)
        + r"\cdot("
        + number(radius)
        + ")^3+"
        + number(m.vertex_height)
        + r"\cdot"
        + number(radius)
        + r"\right)"
    )
    html += line("=" + number(m.result))
    return html


def area(model, entry):
    if entry.get("area_methods") == "all":
        return (
            endpoint_values(model)
            + complete_cube(model)
            + factor_differences(model)
            + "<p><b>Приведём ещё одно решение.</b></p>"
            + translated_area(model, True)
        )
    return translated_area(model, False)
