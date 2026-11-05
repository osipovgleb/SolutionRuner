"""Derive pyramid scale and cut ratios from the geometric relation in the question."""

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import Pyramid


def scaling(body, target, raw, height_only=False):
    if target == "volume" and not height_only and body != "правильного тетраэдра":
        raise ContentPlanError(
            "the reviewed volume-similarity parent uses a regular tetrahedron"
        )
    k = positive(raw, words=True)
    if k <= 1:
        raise ContentPlanError("the growth factor must exceed one")
    power = 1 if height_only else 3 if target == "volume" else 2
    return Pyramid(
        "scale_height"
        if height_only
        else "scale_volume"
        if power == 3
        else "scale_area",
        (k,),
        k**power,
        body,
        {"k": k, "power": sp.Integer(power)},
    )


def cut(kind, given):
    values = tuple(positive(v) for v in given)
    volume = values[0]
    if kind == "edge_cut":
        a, b = values[1:]
        ratio = sp.Max(a, b) / (a + b)
    else:
        ratio = {
            "hex_whole": sp.Integer(6),
            "square_midpoint": sp.Rational(1, 4),
            "midline_cut": sp.Rational(1, 4),
            "box_tetrahedron": sp.Rational(1, 6),
            "cube_center": sp.Rational(1, 6),
        }[kind]
    return Pyramid(
        kind,
        values,
        sp.simplify(volume * ratio),
        q={"V_0": volume, "k": ratio, "V": sp.simplify(volume * ratio)},
    )


def section(kind, given):
    a = positive(given[0])
    side = a / 2
    return Pyramid(kind, (a,), side * side, q={"a": a, "t": side, "S": side * side})
