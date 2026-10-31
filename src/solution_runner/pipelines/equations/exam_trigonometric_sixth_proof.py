"""Keep the sum-of-cubes method when paired sixth powers yield a scaled square."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S


def proof(a):
    from .exam_trigonometric_power_identity import proof as power_proof
    from .exam_trigonometric_proof import candidate_lines, families, formula
    from .exam_trigonometric_variants import argument

    angle = argument(a.scale)
    reduced = sp.expand(sp.rem(a.raw, S * S + C * C - 1, C))
    if a.preferred != S or reduced.has(C) or a.scale != 2 * a.power_angle:
        raise UnsupportedCondition(
            "the scaled sixth-power method must reduce to a sine polynomial at twice the angle"
        )
    html = line(a.original) + power_proof(a.power_angle, fourth_angle=False)
    html += "<p>Подставим полученное тождество в исходное уравнение и приведём подобные слагаемые:</p>"
    html += line(formula(reduced, angle) + "=0")
    for branch in a.branches:
        p = branch.polynomial
        if branch.variable != S or sp.degree(p, S) != 2 or p.coeff(S) != 0:
            raise UnsupportedCondition(
                "the paired sixth powers must yield a square of sine"
            )
        square = sp.cancel(-p.subs(S, 0) / p.coeff(S, 2))
        html += line(formula(S * S, angle) + "=" + sp.latex(square))
        html += candidate_lines(branch, angle=angle, root_scale=a.scale)
    html += "<p>Объединим серии с учётом периода квадрата синуса:</p>"
    for family in families(a):
        html += line(family + r",\quad k\in\mathbb Z")
    return (
        "<p>Применим формулу суммы кубов и основное тригонометрическое тождество:</p>",
        html,
    )
