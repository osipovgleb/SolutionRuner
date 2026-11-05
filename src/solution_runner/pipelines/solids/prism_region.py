"""Recognize reviewed volume witnesses from actual regular-prism vertex subsets."""

from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .regular_prism_geometry import frame

KIND = "regular_vertex_volume"


def polygon_area(points, names):
    if len(names) < 3 or len({n.endswith("_1") for n in names}) != 1:
        raise ContentPlanError(
            "a horizontal polygon with at least three vertices is required"
        )
    ordered = tuple(sorted(names, key=lambda n: n[0]))
    twice = sum(
        points[a][0] * points[b][1] - points[b][0] * points[a][1]
        for a, b in zip(ordered, ordered[1:] + ordered[:1])
    )
    return sp.simplify(sp.Abs(twice) / 2)


def tetra_volume(points, names):
    if len(names) != 4:
        raise ContentPlanError("four distinct tetrahedron vertices are required")
    origin = points[names[0]]
    return sp.simplify(
        sp.Abs(sp.det(sp.Matrix.hstack(*(points[n] - origin for n in names[1:])))) / 6
    )


@dataclass(frozen=True)
class PrismRegion:
    body: str
    vertices: tuple[str, ...]
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    method: str
    fraction: sp.Expr
    base: tuple[str, ...] = ()
    apex: str | None = None
    removed: tuple[tuple[str, ...], ...] = ()
    base_fraction: sp.Expr = sp.S.One
    kind: str = KIND


def _pyramid(body, names, layers, points, full_area):
    for level in (0, 1):
        base, upper = layers[level], layers[1 - level]
        if len(base) < 3 or len(upper) != 1:
            continue
        coefficient = sp.simplify(polygon_area(points, base) / full_area)
        if coefficient != 1 and not (
            body == "hexagon" and coefficient == sp.Rational(1, 6)
        ):
            raise ContentPlanError("this pyramid base needs a reviewed area proof")
        return "pyramid", coefficient / 3, base, upper[0], (), coefficient
    return None


def _paired(body, names, layers, points, full_area):
    lower, upper = layers
    if len(lower) < 3 or {n[0] for n in lower} != {n[0] for n in upper}:
        return None
    coefficient = sp.simplify(polygon_area(points, lower) / full_area)
    if body != "hexagon" or coefficient not in {sp.Rational(1, 6), sp.Rational(2, 3)}:
        raise ContentPlanError("this prism base needs a reviewed area proof")
    return "prism", coefficient, lower, None, (), coefficient


def _subtraction(body, names, layers, points, full_area):
    if body != "triangle" or len(names) not in (4, 5):
        raise ContentPlanError("the vertex subset needs a reviewed volume witness")
    missing = tuple(n for n in points if n not in names)
    removed = tuple(
        tuple(n for n in points if n.endswith("_1") == m.endswith("_1"))
        + (m[0] if m.endswith("_1") else m + "_1",)
        for m in missing
    )
    volumes = tuple(tetra_volume(points, t) for t in removed)
    if any(sp.simplify(v / full_area) != sp.Rational(1, 3) for v in volumes):
        raise ContentPlanError(
            "the removed pyramids must share the whole prism base and height"
        )
    fraction = sp.simplify((full_area - sum(volumes)) / full_area)
    if len(names) == 4 and tetra_volume(points, names) != full_area * fraction:
        raise ContentPlanError("the removed pyramids do not partition this prism")
    return "subtract", fraction, (), None, removed, sp.S.One


def solve(body, names, given):
    if body not in {"triangle", "hexagon"}:
        raise ContentPlanError("a reviewed regular prism body is required")
    points = frame(body)
    if len(set(names)) != len(names) or any(n not in points for n in names):
        raise ContentPlanError("distinct vertices of the named prism are required")
    names = tuple(n for n in points if n in names)
    layers = tuple(
        tuple(n for n in names if n.endswith("_1") == bool(level)) for level in (0, 1)
    )
    full_area = polygon_area(points, tuple(n for n in points if not n.endswith("_1")))
    witness = (
        _pyramid(body, names, layers, points, full_area)
        or _paired(body, names, layers, points, full_area)
        or _subtraction(body, names, layers, points, full_area)
    )
    method, fraction, base, apex, removed, base_fraction = witness
    if fraction.is_positive is not True:
        raise ContentPlanError("a nondegenerate three-dimensional region is required")
    area, height = tuple(positive(v) for v in given)
    return PrismRegion(
        body,
        names,
        (area, height),
        sp.simplify(area * height * fraction),
        method,
        fraction,
        base,
        apex,
        removed,
        base_fraction,
    )
