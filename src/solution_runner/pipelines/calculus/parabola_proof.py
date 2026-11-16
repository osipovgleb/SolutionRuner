"""One endpoint-value solution, keeping the additive constant uncombined."""

import sympy as sp

from ..probability.common import line
from .common import X
from .graph_integral_proof import difference_name, number, substitution


def _signed(value):
    if value == 0:
        return ""
    return ("+" if value > 0 else "-") + number(abs(value))


def endpoint_values(model):
    constant = sp.Poly(model.primitive, X).nth(0)
    variable_part = model.primitive - constant
    upper = variable_part.subs(X, model.upper)
    lower = variable_part.subs(X, model.lower)
    upper_separate = number(upper) + _signed(constant)
    lower_separate = number(lower) + _signed(constant)
    html = "<p>Площадь выделенной фигуры равна разности значений данной первообразной на границах:</p>"
    for value, separate in (
        (model.upper, upper_separate),
        (model.lower, lower_separate),
    ):
        html += line(
            "F("
            + number(value)
            + ")="
            + substitution(model.primitive, value)
            + "="
            + substitution(model.primitive, value, False)
            + "="
            + separate
        )
    html += line(
        "S="
        + difference_name(model)
        + "="
        + r"\left("
        + upper_separate
        + r"\right)-\left("
        + lower_separate
        + r"\right)"
        + "="
        + number(upper)
        + _signed(-lower)
        + "="
        + number(model.result)
    )
    return html
