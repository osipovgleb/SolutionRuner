"""Compute solid volumes from proved base-height ratios and complete positive data."""

from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import UnsupportedCondition
from .box_coordinates import axes, dimensions
from .box_geometry_input import assignments
from .polyhedron_geometry import Polyhedron, recognize
from .polyhedron_input import read_condition


@dataclass(frozen=True)
class PolyhedronVolume:
    solid: Polyhedron
    given: tuple[tuple[str, sp.Expr], ...]
    squares: tuple[sp.Expr, ...]
    box_volume: sp.Expr
    answer: sp.Expr


def read_question(html, source=None, *, preferred_axis=None):
    names, mode, raw, kind = read_condition(html, source)
    solid = recognize(names, preferred_axis=preferred_axis)
    if (
        kind == "prism"
        and solid.kind != "prism"
        or kind == "pyramid"
        and len(names) != 4
    ):
        raise ContentPlanError(
            "the requested solid contradicts its named geometric type"
        )
    if mode == "edges":
        given = assignments(raw)
        if any(len(axes(name)) != 1 for name, _ in given):
            raise ContentPlanError("the volume method requires three box edge lengths")
        squares = dimensions(given)
        total = sp.sqrt(sp.prod(squares))
    else:
        given = ()
        squares = ()
        try:
            total = ScalarParser(raw).parse()
        except UnsupportedCondition as exc:
            raise ContentPlanError(str(exc)) from exc
        if (
            total.is_positive is not True
            or total.is_real is not True
            or total.is_finite is not True
        ):
            raise ContentPlanError(
                "a positive finite total parallelepiped volume is required"
            )
    return PolyhedronVolume(
        solid, given, squares, total, sp.simplify(total * solid.fraction)
    )
