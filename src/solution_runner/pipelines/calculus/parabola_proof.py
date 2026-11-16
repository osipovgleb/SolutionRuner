"""One endpoint-value solution, keeping the additive constant uncombined."""

import sympy as sp

from ..probability.common import line
from .common import X
from .graph_integral_proof import difference_name, number


def _signed(value):
    if value == 0:
        return ""
    return ("+" if value > 0 else "-") + number(abs(value))


def _substitution(primitive, value, *, powers=True):
    """Keep term signs outside magnitudes and bracket negative arguments."""
    polynomial = sp.Poly(primitive, X)
    terms = []
    for degree in range(polynomial.degree(), -1, -1):
        coefficient = polynomial.nth(degree)
        if coefficient == 0:
            continue
        if degree and powers:
            argument = number(value)
            if value < 0 or value.q != 1:
                argument = "(" + argument + ")"
            power = argument + ("^{" + str(degree) + "}" if degree > 1 else "")
            magnitude = (
                power
                if abs(coefficient) == 1
                else number(abs(coefficient)) + r"\cdot" + power
            )
            negative = coefficient < 0
        else:
            evaluated = coefficient * value**degree
            if evaluated == 0:
                continue
            magnitude = number(abs(evaluated))
            negative = evaluated < 0
        terms.append(("-" if negative else "+", magnitude))
    if not terms:
        return "0"
    return "".join(
        (sign if index or sign == "-" else "") + magnitude
        for index, (sign, magnitude) in enumerate(terms)
    )


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
            + _substitution(model.primitive, value)
            + "="
            + _substitution(model.primitive, value, powers=False)
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
