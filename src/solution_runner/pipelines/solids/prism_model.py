"""Exact prism quantities from actual base shape, requested dimension and section geometry."""

from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .polyhedron_geometry import Polyhedron, recognize


@dataclass(frozen=True)
class PrismQuantity:
    kind: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    base: str = ""
    area: sp.Expr = sp.S.Zero
    perimeter: sp.Expr = sp.S.Zero
    height: sp.Expr = sp.S.Zero
    side: sp.Expr = sp.S.Zero
    ratio: sp.Expr = sp.S.One
    solid: Polyhedron | None = None


BASES = {
    "triangle": lambda a, b: (
        a * b / 2,
        a + b + sp.sqrt(a * a + b * b),
        sp.sqrt(a * a + b * b),
    ),
    "rhombus": lambda a, b: (
        a * b / 2,
        2 * sp.sqrt(a * a + b * b),
        sp.sqrt(a * a + b * b) / 2,
    ),
    "square": lambda a, b: (a * a, 4 * a, a),
    "hexagon": lambda a, b: (3 * sp.sqrt(3) * a * a / 2, 6 * a, a),
}
MEASUREMENTS = {
    "triangle_volume": ("triangle", "volume"),
    "triangle_height_volume": ("triangle", "height_volume"),
    "triangle_total": ("triangle", "total"),
    "triangle_height_total": ("triangle", "height_total"),
    "rhombus_total": ("rhombus", "total"),
    "rhombus_height_total": ("rhombus", "height_total"),
    "square_height_total": ("square", "height_total"),
    "hex_lateral": ("hexagon", "lateral"),
    "hex_volume": ("hexagon", "volume"),
    "hex_equal_volume": ("hexagon", "volume"),
    "normal_lateral": ("triangle", "lateral"),
}


def measurement(kind, given):
    values = tuple(positive(v) for v in given)
    shape, target = MEASUREMENTS[kind]
    a = values[0]
    b = values[1] if shape in {"triangle", "rhombus"} else sp.S.Zero
    area, perimeter, side = BASES[shape](a, b)
    last = values[-1]
    height = last
    if target == "height_volume":
        height = last / area
    elif target == "height_total":
        height = (last - 2 * area) / perimeter
    if height.is_positive is not True:
        raise ContentPlanError("the prism height must be positive")
    answers = {
        "volume": area * height,
        "lateral": perimeter * height,
        "total": 2 * area + perimeter * height,
        "height_volume": height,
        "height_total": height,
    }
    return PrismQuantity(
        kind,
        values,
        sp.simplify(answers[target]),
        shape,
        area,
        perimeter,
        sp.simplify(height),
        side,
    )


def acute(raw):
    angle = positive(raw)
    if angle not in {30, 45, 60}:
        raise ContentPlanError(
            "the prism method requires a reviewed acute standard angle"
        )
    return angle


def oblique(kind, given):
    if kind == "oblique_rhombus":
        a, alpha, edge, beta = given
        a, edge = positive(a), positive(edge)
        alpha, beta = acute(alpha), acute(beta)
        area = a * a * sp.sin(sp.pi * alpha / 180)
        values = (a, alpha, edge, beta)
        shape = "rhombus"
    else:
        a, edge, beta = given
        a, edge = positive(a), positive(edge)
        beta = acute(beta)
        area = BASES["hexagon"](a, sp.S.Zero)[0]
        values = (a, edge, beta)
        shape = "hexagon"
    height = edge * sp.sin(sp.pi * beta / 180)
    return PrismQuantity(
        kind,
        values,
        sp.simplify(area * height),
        base=shape,
        area=sp.simplify(area),
        height=sp.simplify(height),
        side=a,
    )


def section(kind, given):
    a, h = (positive(v) for v in given)
    width = a / 2 if kind == "midline_section" else a * sp.sqrt(3) / 2
    return PrismQuantity(kind, (a, h), sp.simplify(width * h), height=h, side=width)


def diagonal(given):
    h, d = (positive(v) for v in given)
    if d <= h:
        raise ContentPlanError("the prism space diagonal must exceed its height")
    width = sp.sqrt(d * d - h * h)
    return PrismQuantity(
        "diagonal_section", (h, d), sp.simplify(width * h), height=h, side=width
    )


def vertex_volume(given, names):
    area, h = (positive(v) for v in given)
    solid = recognize(names)
    if solid.kind != "pyramid":
        raise ContentPlanError("these prism vertices need a reviewed pyramid proof")
    return PrismQuantity(
        "vertex_volume",
        (area, h),
        sp.simplify(area * h * solid.fraction),
        area=area,
        height=h,
        side=sp.sqrt(area),
        solid=solid,
    )


def read_question(html, source=None):
    from .prism_reader import read

    return read(html, source)
