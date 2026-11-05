"""Express exact component lengths using the marked segment names of each diagram."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value

ALIASES = {
    "step": {
        "width": "AB",
        "depth": "A_2D_2",
        "height": "AA_2",
        "rise": "D_1C_2",
        "upper_width": "D_2C_2",
    },
    "ridge": {
        "width": "DC",
        "depth": "BC",
        "base_height": "CC_1",
        "rise": "C_2C_3",
        "upper_width": "D_3C_3",
        "right_ledge": "C_2C_1",
    },
    "elbow": {
        "width": "FE",
        "height": "FD_2",
        "upper_width": "D_2C_2",
        "upper_depth": "A_2D_2",
        "depth": "AF",
    },
}


def tex(m, expression, *, numeric=False):
    labels = (
        {k: value(sp.Rational(v)) for k, v in m.given.items()}
        if numeric
        else ALIASES[m.kind]
    )
    symbols = {sp.Symbol(k, positive=True): v for k, v in labels.items()}
    return sp.latex(expression, symbol_names=symbols)


def name(raw):
    return "<i>" + re.sub(r"_([123])", r"<sub>\1</sub>", raw) + "</i>"


def components(m, a, b):
    numeric = m.points[b] - m.points[a]
    symbolic = m.symbolic[b] - m.symbolic[a]
    result = []
    for actual, expression in zip(numeric, symbolic, strict=True):
        if actual:
            result.append(
                (sp.expand(expression if actual > 0 else -expression), sp.Abs(actual))
            )
    if not result or len(result) > 2:
        raise ContentPlanError(
            "a parent triangle leg must lie on a reviewed edge or face"
        )
    return tuple(result)


def square_terms(m, parts, *, numeric=False):
    return "+".join(
        r"\left(" + tex(m, expr, numeric=numeric) + r"\right)^2" for expr, _ in parts
    )


def equalities(*terms):
    unique = []
    for term in terms:
        if not unique or unique[-1] != term:
            unique.append(term)
    return "=".join(unique)


def edge_row(m, a, b):
    parts = components(m, a, b)
    if len(parts) != 1:
        raise ContentPlanError("the named leg is not a single orthogonal edge")
    expr, actual = parts[0]
    return line(
        equalities(a + b, tex(m, expr), tex(m, expr, numeric=True), value(actual))
    )


def leaf_rows(m, a, b):
    parts = components(m, a, b)
    if len(parts) == 1:
        return edge_row(m, a, b)
    label = a + b + "^2"
    return (
        line(label + "=" + square_terms(m, parts))
        + line(label + "=" + square_terms(m, parts, numeric=True))
        + line(
            label
            + "="
            + "+".join(value(n * n) for _, n in parts)
            + "="
            + value(sum(n * n for _, n in parts))
        )
    )
