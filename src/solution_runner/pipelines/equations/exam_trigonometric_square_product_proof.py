"""Explain a zero sine/cosine factor followed by a complete square."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def proof(a):
    from .exam_trigonometric_proof import candidate_lines, formula
    from .exam_trigonometric_square_factor import square
    from .exam_trigonometric_variants import argument

    zero, quadratic = a.square_product
    variable = C if zero.has(S) else S
    angle = argument(a.scale)
    html = "".join(
        line(text + "=" + formula(value, angle)) for text, value in a.identities
    )
    if a.factored_source is not None:
        html += line(formula(a.factored_source, angle) + "=0")
        html += line(formula(S * S + C * C, angle) + "=1")
    html += line(formula(a.raw, angle) + "=0")
    html += "<p>Вынесем общий тригонометрический множитель, не деля на него:</p>"
    html += line(formula(sp.Mul(zero, quadratic, evaluate=False), angle) + "=0")
    html += "<p>В оставшейся скобке выделим полный квадрат:</p>"
    html += line(
        formula(sp.Mul(zero, square(quadratic, variable), evaluate=False), angle) + "=0"
    )
    html += "<p>Сначала решим уравнение для нулевого множителя, затем для квадратной скобки:</p>"
    for branch in a.branches:
        html += candidate_lines(branch, angle=angle, root_scale=a.scale)
    return (
        "<p>Применим тригонометрические тождества и сохраним все нулевые множители:</p>",
        html,
    )
