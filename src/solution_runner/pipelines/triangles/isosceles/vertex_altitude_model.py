"""Read exact included-angle/side-altitude inverse pairs with actual vertex names."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .cosine_model import _DEGREE, _SEGMENT
from .side_altitude_model import _setup

RULES = {
    "isosceles-triangle-27795-altitude-from-side-vertex-angle": ("side_angle", {-1, 0}),
    "isosceles-triangle-27796-angle-from-side-altitude": ("side_height", {-1}),
    "isosceles-triangle-27797-side-from-altitude-vertex-angle": (
        "height_angle",
        {-1, 0, 1},
    ),
    "isosceles-triangle-27798-obtuse-altitude-from-side-angle": ("side_angle", {1}),
}


@dataclass(frozen=True)
class VertexAltitudeTriangle:
    mode: str
    vertex: str
    apex: str
    apex_angle: sp.Rational
    side_raw: str | None
    height_raw: str | None
    requested: str

    @property
    def other_base_vertex(self):
        return (set("ABC") - {self.vertex, self.apex}).pop()

    @property
    def side_segment(self):
        return "".join(sorted((self.vertex, self.apex)))

    @property
    def other_side(self):
        return "".join(sorted((self.other_base_vertex, self.apex)))

    @property
    def height_segment(self):
        return self.vertex + "H"

    @property
    def sine(self):
        return sp.simplify(sp.sin(sp.pi * self.apex_angle / 180))

    @property
    def side(self):
        return (
            _parse_positive_value(self.side_raw)
            if self.side_raw is not None
            else sp.simplify(self.height / self.sine)
        )

    @property
    def height(self):
        return (
            _parse_positive_value(self.height_raw)
            if self.height_raw is not None
            else sp.simplify(self.side * self.sine)
        )

    @property
    def projection(self):
        return sp.simplify(self.side * abs(sp.cos(sp.pi * self.apex_angle / 180)))

    @property
    def topology(self):
        return 0 if self.apex_angle == 90 else -1 if self.apex_angle < 90 else 1

    @property
    def answer(self):
        return (
            self.height
            if self.mode == "side_angle"
            else self.side
            if self.mode == "height_angle"
            else self.apex_angle
        )

    def require_rule(self, rule):
        mode, topologies = RULES.get(rule, (None, set()))
        if self.mode != mode or self.topology not in topologies:
            raise ContentPlanError(
                "the complete vertex-altitude question differs from its registered rule"
            )
        return self


def _facts(rest, side):
    lengths = {} if side is None else {"side": side}
    angle = None
    height = None
    while rest.strip(" ,."):
        rest = rest.lstrip(" ,.")
        degree = re.match(r"угол ([ABC]) равен " + _DEGREE, rest)
        assigned = re.match(r"высота ([ABC]H) равна\s*", rest)
        defined = re.match(r"([ABC]H)\s*[—–-]\s*высота\b", rest)
        segment = re.match(r"(" + _SEGMENT + r"|[ABC]H|H[ABC])\s*=\s*", rest)
        if degree and angle is None:
            angle = (
                degree[1],
                sp.Rational(degree[2].replace("{,}", ".").replace(",", ".")),
            )
            rest = rest[degree.end() :]
            continue
        if assigned or defined:
            match = assigned or defined
            if height is not None:
                raise ContentPlanError("the side altitude must be defined once")
            height = match[1]
            rest = rest[match.end() :]
            if defined:
                continue
            key = height
        elif segment:
            key = "".join(sorted(segment[1]))
            rest = rest[segment.end() :]
        else:
            raise ContentPlanError("an unreviewed vertex-altitude statement remains")
        if key in lengths:
            raise ContentPlanError("duplicate vertex-altitude length givens")
        raw, rest = _value(rest)
        lengths[key] = raw
    return lengths, angle, height


def _targets(request, height):
    target_height = re.fullmatch(r"\s*высоту ([ABC]H)\s*\.\s*", request)
    target_side = re.fullmatch(r"\s*(" + _SEGMENT + r")\s*\.\s*", request)
    target_angle = re.fullmatch(
        r"\s*(?:угол ([ABC])\s*\.\s*Ответ дайте в градусах\.|градусную меру угла ([ABC])\s*\.?)\s*",
        request,
    )
    if target_height:
        if height is not None and height != target_height[1]:
            raise ContentPlanError("the defined and requested altitudes must coincide")
        height = target_height[1]
    return height, target_height, target_side, target_angle


def _lengths(lengths, apex, height):
    sides = {"".join(sorted((v, apex))) for v in set("ABC") - {apex}}
    side_keys = set(lengths) & ({"side"} | sides)
    if len(side_keys) > 1:
        raise ContentPlanError("one independent equal-side length is required")
    side_raw = lengths[next(iter(side_keys))] if side_keys else None
    height_raw = lengths.get(height)
    if set(lengths) != (side_keys | ({height} if height_raw is not None else set())):
        raise ContentPlanError("only the equal side and its altitude may be given")
    return side_raw, height_raw, sides


def read_question(html, source):
    try:
        text = _text(html, source)
        if text.count("Найдите") != 1:
            raise ContentPlanError("one complete vertex-altitude question is required")
        given, request = text.split("Найдите")
        acute = re.match(r"[ВB] остроугольном треугольнике ABC известно, что\s*", given)
        if acute:
            given = "B треугольнике ABC " + given[acute.end() :]
        apex, side, rest = _setup(given)
        lengths, degree, height = _facts(rest, side)
        height, target_height, target_side, target_angle = _targets(request, height)
        if height is None or height[0] == apex:
            raise ContentPlanError("a side altitude must start at a base vertex")
        vertex = height[0]
        side_raw, height_raw, sides = _lengths(lengths, apex, height)
        if (
            target_height
            and side_raw is not None
            and height_raw is None
            and degree is not None
        ):
            mode = "side_angle"
            requested = height
        elif (
            target_side
            and side_raw is None
            and height_raw is not None
            and degree is not None
            and "".join(sorted(target_side[1])) in sides
        ):
            mode = "height_angle"
            requested = "".join(sorted(target_side[1]))
        elif (
            target_angle
            and acute
            and side_raw is not None
            and height_raw is not None
            and degree is None
            and (target_angle[1] or target_angle[2]) == apex
        ):
            ratio = sp.simplify(
                _parse_positive_value(height_raw) / _parse_positive_value(side_raw)
            )
            if (1 - ratio).is_positive is not True:
                raise ContentPlanError(
                    "the acute-triangle side altitude must be shorter than its side"
                )
            degree = (apex, sp.simplify(180 * sp.asin(ratio) / sp.pi))
            mode = "side_height"
            requested = apex
        else:
            raise ContentPlanError(
                "one complete direct or inverse side-altitude question is required"
            )
        if (
            degree[0] != apex
            or degree[1].is_Rational is not True
            or not 0 < degree[1] < 180
            or (acute and degree[1] >= 90)
        ):
            raise ContentPlanError(
                "the requested included angle must be exact and consistent with the triangle type"
            )
        model = VertexAltitudeTriangle(
            mode, vertex, apex, degree[1], side_raw, height_raw, requested
        )
        if model.sine.has(sp.sin):
            raise ContentPlanError("an exact supported sine is required")
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
