"""Exact supplementary-angle geometry for an isosceles side altitude."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .side_altitude_model import _setup

RULES = {
    "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude": (
        "side_height",
        "sin",
    ),
    "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude": (
        "side_height",
        "cos",
    ),
    "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude": (
        "side_height",
        "tg",
    ),
    "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection": (
        "side_projection",
        "cos",
    ),
    "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection": (
        "side_projection",
        "tg",
    ),
    "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection": (
        "height_projection",
        "sin",
    ),
    "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection": (
        "height_projection",
        "cos",
    ),
    "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection": (
        "height_projection",
        "tg",
    ),
}


@dataclass(frozen=True)
class ObtuseTriangle:
    vertex: str
    apex: str
    other_base_vertex: str
    givens: dict[str, tuple[sp.Expr, str]]
    given_kind: str
    function: str
    requested: str
    side: sp.Expr
    height: sp.Expr
    projection: sp.Expr

    @property
    def answer(self):
        return sp.simplify(
            {
                "sin": self.height / self.side,
                "cos": -self.projection / self.side,
                "tg": -self.height / self.projection,
            }[self.function]
        )

    def require_rule(self, rule):
        if RULES.get(rule) != (self.given_kind, self.function):
            raise ContentPlanError(
                "the complete obtuse question differs from the registered rule"
            )
        return self


def _facts(rest, side):
    lengths = {} if side is None else {"side": (_parse_positive_value(side), side)}
    height = None
    while rest.strip(" ,."):
        rest = rest.lstrip(" ,.")
        definition = re.match(r"([ABC]H)\s*[—–−-]\s*высота\b", rest)
        assigned = re.match(r"высота ([ABC]H) равна\s*", rest)
        if definition or assigned:
            match = definition or assigned
            if height is not None:
                raise ContentPlanError("the obtuse side altitude must be defined once")
            height = match[1]
            rest = rest[match.end() :]
            if definition:
                continue
            key = height
        else:
            match = re.match(r"(AB|BA|AC|CA|BC|CB|AH|HA|BH|HB|CH|HC)\s*=\s*", rest)
            if match is None:
                raise ContentPlanError("an unreviewed obtuse statement remains")
            key = "".join(sorted(match[1]))
            rest = rest[match.end() :]
        if key in lengths:
            raise ContentPlanError("duplicate obtuse length givens")
        raw, rest = _value(rest)
        lengths[key] = (_parse_positive_value(raw), raw)
    return lengths, height


def _request(text, apex):
    match = re.fullmatch(
        r"\s*(?:\\(sin|cos|tg)\s*(?:\\angle\s*)?([ABC]{3})|"
        r"(синус|косинус|тангенс) угла ([ABC]{3}))\s*\.?\s*",
        text,
    )
    if match is None:
        raise ContentPlanError("the complete obtuse trigonometric request is required")
    function = match[1] or {"синус": "sin", "косинус": "cos", "тангенс": "tg"}[match[3]]
    angle = match[2] or match[4]
    if set(angle) != set("ABC") or angle[1] != apex:
        raise ContentPlanError("the requested angle must be the obtuse vertex angle")
    return function, angle


def _geometry(lengths, sides, height, projection):
    normalized = {}
    for key, value in lengths.items():
        name = "side" if key == "side" or key in sides else key
        if name in normalized:
            raise ContentPlanError("two independent obtuse lengths are required")
        normalized[name] = value
    names = set(normalized)
    if names == {"side", height}:
        s, h = normalized["side"][0], normalized[height][0]
        difference = sp.simplify(s**2 - h**2)
        if difference.is_positive is not True:
            raise ContentPlanError("the altitude must be shorter than the equal side")
        return normalized, "side_height", s, h, sp.sqrt(difference)
    if names == {"side", projection}:
        s, p = normalized["side"][0], normalized[projection][0]
        difference = sp.simplify(s**2 - p**2)
        if difference.is_positive is not True:
            raise ContentPlanError("the projection must be shorter than the equal side")
        return normalized, "side_projection", s, sp.sqrt(difference), p
    if names == {height, projection}:
        h, p = normalized[height][0], normalized[projection][0]
        return normalized, "height_projection", sp.sqrt(sp.simplify(h**2 + p**2)), h, p
    raise ContentPlanError("exactly two reviewed obtuse length givens are required")


def read_question(html, source):
    try:
        text = _text(html, source)
        prefix = re.match(r"[ВB] тупоугольном треугольнике ABC\s+", text)
        if prefix is None or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete explicitly obtuse question is required"
            )
        given, request = text[prefix.end() :].split("Найдите")
        apex, side, rest = _setup("B треугольнике ABC " + given)
        lengths, height = _facts(rest, side)
        if height is None or height[0] == apex:
            raise ContentPlanError("an altitude from a base vertex must be defined")
        vertex = height[0]
        other = (set("ABC") - {apex, vertex}).pop()
        sides = {"".join(sorted((v, apex))) for v in (vertex, other)}
        values, kind, s, h, p = _geometry(lengths, sides, height, apex + "H")
        function, angle = _request(request, apex)
        return ObtuseTriangle(
            vertex, apex, other, values, kind, function, angle, s, h, p
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
