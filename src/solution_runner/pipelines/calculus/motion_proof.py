"""Velocity as one derivative chain, then a value or a velocity equation."""

import sympy as sp

from ..probability.common import line
from .common import T


def number(value):
    value = sp.sympify(value)
    text = sp.latex(value)
    return (
        r"\left(" + text + r"\right)"
        if value < 0 or value.is_Integer is not True
        else text
    )


def render(law, velocity, value, evaluate, result, roots=()):
    html = "<p>Скорость равна производной закона движения:</p>"
    html += line(
        "V(t)=x'(t)=" + r"\left(" + sp.latex(law) + r"\right)'=" + sp.latex(velocity)
    )
    if evaluate:
        substitution = sp.latex(
            velocity, symbol_names={T: number(value)}, mul_symbol="dot"
        )
        html += "<p>Найдём скорость в заданный момент времени:</p>"
        calculation = substitution
        if substitution != sp.latex(result):
            calculation += "=" + sp.latex(result)
        html += line("V(" + sp.latex(value) + ")=" + calculation + r"\;\text{м/с}")
    else:
        html += "<p>Приравняем скорость заданному значению:</p>"
        html += line("V(t)=" + sp.latex(value))
        html += line(sp.latex(velocity) + "=" + sp.latex(value))
        equation = sp.expand(velocity - value)
        if sp.Poly(equation, T).degree() == 1:
            a, b = sp.Poly(equation, T).all_coeffs()
            html += line(sp.latex(a * T) + "=" + sp.latex(-b))
            html += line("t=" + sp.latex(result) + r"\;\text{с}")
            return html
        from ..function_graphs.parabola_proof import quadratic_steps

        html += "<p>Решим квадратное уравнение через дискриминант:</p>"
        from bs4 import BeautifulSoup

        steps = BeautifulSoup(quadratic_steps(equation, T, roots), "html.parser")
        from ..word_problems.math_common import primitive

        polynomial = sp.Poly(primitive(equation, (T,)), T)
        a, b, c = polynomial.all_coeffs()
        discriminant = b**2 - 4 * a * c
        for node in steps.select("[data-inline-latex]"):
            formula = node["data-inline-latex"].split(r"\in\left\{", 1)[0]
            if r"\pm" in formula:
                rows = []
                for sign, symbol in ((-1, "-"), (1, "+")):
                    root = sp.simplify((-b + sign * sp.sqrt(discriminant)) / (2 * a))
                    row = formula.replace("t=", "t&=", 1).replace(r"\pm", symbol)
                    rows.append(row + "=" + sp.latex(root))
                    if discriminant == 0:
                        break
                formula = (
                    r"\left[\begin{aligned}"
                    + r"\\".join(rows)
                    + r"\end{aligned}\right."
                    if len(rows) > 1
                    else rows[0].replace("t&=", "t=", 1)
                )
            node["data-inline-latex"] = (
                r"\displaystyle " + formula if r"\frac" in formula else formula
            )
        html += str(steps)
        if any(r.is_nonnegative is not True for r in roots):
            html += "<p>Время отсчитывается от начала движения, поэтому отрицательный корень не подходит.</p>"
        html += line("t=" + sp.latex(result) + r"\;\text{с}")
    return html
