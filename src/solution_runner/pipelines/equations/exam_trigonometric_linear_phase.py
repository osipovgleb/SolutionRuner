"""Recognize a shifted sine at its exact extreme in a linear factor."""

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
    if not a or not b or not constant or sp.simplify(a * a + b * b - constant**2) != 0:
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
    residues = ordered((q - phase) % 2 for q in angles(S, value))
    return Branch(
        S,
        S - value,
        (value,),
        (value,),
        residues,
        original=expression,
        angle_shift=phase,
    )


def proof(branch, angle, root_scale):
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
    html += (
        "<p>Применим формулу синуса суммы и получим уравнение для сдвинутого угла:</p>"
    )
    html += line(
        formula(expression, angle) + "=" + formula(amplitude * S + constant, shifted)
    )
    html += line(formula(S, shifted) + "=" + sp.latex(branch.values[0]))
    series = tuple(
        ((q - branch.angle_shift) / root_scale, period / root_scale)
        for q, period in level_series(S, branch.values[0])
    )
    for text in series_lines(series):
        html += line(text + r",\quad k\in\mathbb Z")
    return html
