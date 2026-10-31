"""Recognize reviewed shifted functions in an affine sine/cosine factor."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def branch(expression):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_inverse import angles, ordered

    if expression.free_symbols != {S, C} or not expression.is_polynomial(S, C):
        return None
    if sp.Poly(expression, S, C).total_degree() != 1:
        return None
    a, b = expression.coeff(S), expression.coeff(C)
    constant = expression.subs({S: 0, C: 0})
    if not a or not b or not constant:
        return None
    amplitude = sp.sqrt(sp.simplify(a * a + b * b))
    phases = [
        sp.Rational(n, 12)
        for n in range(-11, 13)
        if sp.simplify(amplitude * sp.cos(sp.pi * n / 12) - a) == 0
        and sp.simplify(amplitude * sp.sin(sp.pi * n / 12) - b) == 0
    ]
    if len(phases) != 1:
        return None
    phase = phases[0]
    value = sp.simplify(-constant / amplitude)
    from ..word_problems.common import UnsupportedCondition

    try:
        roots = angles(S, value)
    except UnsupportedCondition:
        return None
    residues = ordered((q - phase) % 2 for q in roots)
    return Branch(
        S,
        S - value,
        (value,),
        (value,),
        residues,
        original=expression,
        angle_shift=phase,
    )


def notation(branches, parent_html, *, scale=sp.S.One):
    from bs4 import BeautifulSoup

    from .exam_trigonometric_shifted import candidates, formula

    functions = {
        name
        for node in BeautifulSoup(parent_html, "html.parser").select(
            "[data-inline-latex]"
        )
        for name, _, _ in candidates(
            formula(node["data-inline-latex"]), argument_scale=scale
        )
    }
    if functions != {"cos"}:
        return branches
    result = []
    for b in branches:
        if b.angle_shift:
            phase = (b.angle_shift - sp.Rational(1, 2) + 1) % 2 - 1
            b = replace(
                b, variable=C, polynomial=C - b.candidates[0], angle_shift=phase
            )
        result.append(b)
    return tuple(result)


def proof(branch, angle, root_scale, allowed_residues=None):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import formula, series_lines

    expression = branch.original
    amplitude = sp.sqrt(
        sp.simplify(expression.coeff(S) ** 2 + expression.coeff(C) ** 2)
    )
    constant = expression.subs({S: 0, C: 0})
    shifted = (
        r"\left(" + angle + "+(" + sp.latex(branch.angle_shift * sp.pi) + r")\right)"
    )
    html = line(formula(expression, angle) + "=0")
    name = "синуса" if branch.variable == S else "косинуса"
    html += (
        "<p>Применим формулу "
        + name
        + " суммы и получим уравнение для сдвинутого угла:</p>"
    )
    html += line(
        formula(expression, angle)
        + "="
        + formula(amplitude * branch.variable + constant, shifted)
    )
    html += line(
        formula(branch.variable, shifted) + "=" + sp.latex(branch.candidates[0])
    )
    series = tuple(
        ((q - branch.angle_shift) / root_scale, period / root_scale)
        for q, period in level_series(branch.variable, branch.candidates[0])
    )
    for text in series_lines(series):
        html += line(text + r",\quad k\in\mathbb Z")
    if allowed_residues is not None:
        html += "<p>После проверки исходной области определения оставляем серии:</p>"
        for text in series_lines(
            tuple((q / root_scale, 2 / root_scale) for q in allowed_residues)
        ):
            html += line(text + r",\quad k\in\mathbb Z")
    return html
