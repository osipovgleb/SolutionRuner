"""Retain a shifted biquadratic substitution and its positive-factor alternative."""

from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def prepare(a, html):
    if a.scale != 1 or a.raw.free_symbols not in ({S}, {C}):
        return a
    variable = next(iter(a.raw.free_symbols))
    if sp.degree(a.raw, variable) != 4:
        return a
    leading = a.raw.coeff(variable, 4)
    shift = sp.cancel(-a.raw.coeff(variable, 3) / (4 * leading))
    if shift.is_Rational is not True or abs(shift) > 10 or shift == 0:
        return a
    t = sp.Symbol("t", real=True)
    polynomial = sp.expand(a.raw.subs(variable, t + shift))
    second = polynomial.coeff(t, 2)
    if (
        leading.is_positive is not True
        or second.is_positive is not True
        or sp.expand(polynomial - leading * t**4 - second * t * t) != 0
    ):
        return a
    formulas = "".join(
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )
    function = "sin" if variable == S else "cos"
    assignment = "\\" + function + "x=t" + ("+" if shift > 0 else "") + sp.latex(shift)
    base = "\\" + function + "x" + ("-" if shift > 0 else "+") + sp.latex(abs(shift))
    substituted = assignment in formulas
    if not substituted and formulas.count(base) < 2:
        return a
    return replace(a, centered_power=(variable, shift, leading, second, substituted))


def proof(a):
    from .exam_trigonometric_proof import families, formula

    variable, shift, leading, second, substituted = a.centered_power
    t = sp.Symbol("t", real=True)
    polynomial = sp.expand(a.raw.subs(variable, t + shift))
    html = line(a.original)
    if substituted:
        html += "<p>Введём сдвинутое обозначение, чтобы исчезли нечётные степени:</p>"
        html += line(formula(variable) + "=" + sp.latex(t + shift))
        from .exam_trigonometric_methods import parse_equation

        values, atoms, _ = parse_equation(a.original)
        if all(
            atom.coefficient == 1
            and atom.shift == 0
            and atom.function == ("sin" if variable == S else "cos")
            for atom in atoms.values()
        ):
            substitution = dict.fromkeys(atoms, t + shift)
            html += line(
                sp.latex(values[0].xreplace(substitution))
                + "="
                + sp.latex(values[1].xreplace(substitution))
            )
        html += line(sp.latex(polynomial) + "=0")
        html += line(sp.latex(sp.factor(polynomial)) + "=0")
        html += "<p>Второй множитель строго положителен для любого действительного t, поэтому равен нулю только квадрат:</p>"
        html += line(sp.latex(t * t + second / leading) + ">0")
        html += line("t=0")
        html += "<p>Вернёмся к исходной переменной:</p>"
    else:
        html += "<p>Раскроем четвёртые степени, приведём подобные слагаемые и выделим квадрат:</p>"
        html += line(formula(a.raw) + "=0")
        html += line(formula(sp.factor(a.raw)) + "=0")
        html += line(
            formula((variable - shift) ** 2)
            + r"\left("
            + formula((variable - shift) ** 2 + second / leading)
            + r"\right)=0"
        )
        html += "<p>Выражение в скобках строго положительно, поэтому квадрат равен нулю.</p>"
    html += line(formula(variable) + "=" + sp.latex(shift))
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Решим уравнение четвёртой степени с учётом его симметрии:</p>", html
