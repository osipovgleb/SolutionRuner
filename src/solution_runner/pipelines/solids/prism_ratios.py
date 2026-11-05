"""Use the actual direction of prism cuts, similar surface scaling and conserved liquid volume."""

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .prism_model import PrismQuantity

COEFFICIENTS = {
    "mid_volume_part": sp.Rational(1, 4),
    "mid_volume_whole": sp.Integer(4),
    "mid_lateral_part": sp.Rational(1, 2),
    "mid_lateral_whole": sp.Integer(2),
    "remove_pyramid": sp.Rational(2, 3),
    "cube_part": sp.Rational(1, 8),
    "cube_whole": sp.Integer(8),
}


def cut(kind, given):
    amount = positive(given[0])
    return PrismQuantity(
        kind,
        (amount,),
        sp.simplify(amount * COEFFICIENTS[kind]),
        ratio=COEFFICIENTS[kind],
    )


def transfer(given):
    height, raw, direction = given
    height, factor = positive(height), positive(raw)
    if factor <= 1:
        raise ContentPlanError("the prism side comparison factor must exceed one")
    ratio = factor if direction == "больше" else 1 / factor
    return PrismQuantity(
        "transfer",
        (height, factor),
        sp.simplify(height / ratio**2),
        height=height,
        ratio=ratio,
    )


def scale(given):
    area, raw, direction = given
    area, factor = positive(area), positive(raw, words=True)
    if factor <= 1:
        raise ContentPlanError("the prism similarity factor must exceed one")
    ratio = factor if direction.startswith("увелич") else 1 / factor
    return PrismQuantity(
        "similar_surface", (area, factor), sp.simplify(area * ratio**2), ratio=ratio
    )
