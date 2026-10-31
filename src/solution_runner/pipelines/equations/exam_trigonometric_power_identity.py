"""Fold a verified sum of sixth powers before changing the base angle."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S

X = sp.Symbol("x", real=True)


def fold_sixth(actual):
    powers = {
        p
        for p in actual.atoms(sp.Pow)
        if p.exp == 6 and p.base.func in (sp.sin, sp.cos)
    }
    if not powers:
        return actual, None
    arguments = {p.base.args[0] for p in powers}
    if len(powers) != 2 or len(arguments) != 1:
        raise UnsupportedCondition("paired sixth powers at the same angle are required")
    angle = arguments.pop()
    multiple = sp.cancel(angle / X)
    if multiple.is_Rational is not True or multiple <= 0 or multiple > 100:
        raise UnsupportedCondition("a bounded positive sixth-power angle is required")
    sine, cosine = sp.sin(angle) ** 6, sp.cos(angle) ** 6
    expanded = sp.expand(actual)
    coefficient = expanded.coeff(sine)
    if (
        not coefficient
        or coefficient.free_symbols
        or expanded.coeff(cosine) != coefficient
    ):
        raise UnsupportedCondition(
            "the two sixth powers need the same scalar coefficient"
        )
    identity = (5 + 3 * sp.cos(4 * angle)) / 8
    if sp.trigsimp(sp.expand_trig(sine + cosine - identity)) != 0:
        raise UnsupportedCondition("the sixth-power identity must hold exactly")
    return sp.expand(
        expanded - coefficient * (sine + cosine) + coefficient * identity
    ), multiple


def proof(multiple):
    from .exam_trigonometric_proof import formula
    from .exam_trigonometric_variants import argument

    angle = argument(multiple)
    html = (
        "<p>Используем формулу суммы кубов и основное тригонометрическое тождество:</p>"
    )
    html += line(
        formula(S**6 + C**6, angle)
        + "="
        + formula((S * S + C * C) * (S**4 - S * S * C * C + C**4), angle)
    )
    html += line(
        formula(S**6 + C**6, angle) + "=" + formula(1 - 3 * S * S * C * C, angle)
    )
    html += line(
        formula(S**6 + C**6, angle)
        + r"=1-\frac{3}{4}"
        + formula(S * S, argument(2 * multiple))
    )
    html += line(
        formula(S**6 + C**6, angle)
        + r"=\frac{5+3"
        + formula(C, argument(4 * multiple))
        + "}{8}"
    )
    return html
