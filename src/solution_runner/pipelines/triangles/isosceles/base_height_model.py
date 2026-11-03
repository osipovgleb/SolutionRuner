"""Read equilateral height pairs and exact vertex angles from base/height data."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .side_altitude_model import _facts, _setup

RULES = {
    "isosceles-triangle-27792-equilateral-height-from-side": "side_to_height",
    "isosceles-triangle-27793-equilateral-side-from-height": "height_to_side",
    "isosceles-triangle-27794-vertex-angle-from-base-altitude": "base_height_to_angle",
}
_SIDE = r"(?:AB|BA|AC|CA|BC|CB)"


@dataclass(frozen=True)
class BaseHeightTriangle:
    mode: str
    vertex: str
    first_raw: str
    second_raw: str | None = None

    @property
    def base_vertices(self):
        return tuple(sorted(set("ABC") - {self.vertex}))

    @property
    def base_segment(self):
        return "".join(self.base_vertices)

    @property
    def side_segment(self):
        return "".join(sorted((self.base_vertices[0], self.vertex)))

    @property
    def height_segment(self):
        return self.vertex + "H"

    @property
    def base(self):
        return (
            _parse_positive_value(self.first_raw)
            if self.mode == "base_height_to_angle"
            else self.side
        )

    @property
    def height(self):
        if self.mode == "side_to_height":
            return sp.simplify(self.side * sp.sqrt(3) / 2)
        return _parse_positive_value(
            self.second_raw if self.mode == "base_height_to_angle" else self.first_raw
        )

    @property
    def side(self):
        value = _parse_positive_value(self.first_raw)
        if self.mode == "side_to_height":
            return value
        if self.mode == "height_to_side":
            return sp.simplify(2 * value / sp.sqrt(3))
        return sp.sqrt(sp.simplify(value**2 / 4 + self.height**2))

    @property
    def apex_angle(self):
        return (
            sp.simplify(360 * sp.atan(self.base / (2 * self.height)) / sp.pi)
            if self.mode == "base_height_to_angle"
            else sp.Integer(60)
        )

    @property
    def answer(self):
        return (
            self.height
            if self.mode == "side_to_height"
            else self.side
            if self.mode == "height_to_side"
            else self.apex_angle
        )

    def require_rule(self, rule):
        if RULES.get(rule) != self.mode:
            raise ContentPlanError(
                "the complete base-height question differs from its registered rule"
            )
        return self


def _equilateral(given, request):
    prefix = re.match(
        r"[ВB] треугольнике ABC\s+("
        + _SIDE
        + r")\s*=\s*("
        + _SIDE
        + r")\s*=\s*("
        + _SIDE
        + r")\s*=\s*",
        given,
    )
    if prefix:
        if {"".join(sorted(s)) for s in prefix.groups()} != {"AB", "AC", "BC"}:
            raise ContentPlanError(
                "three distinct equal sides must define the equilateral triangle"
            )
        raw, rest = _value(given[prefix.end() :])
        target = re.fullmatch(r"\s*высоту ([ABC])H\s*\.\s*", request)
        if rest.strip(" .") or target is None:
            raise ContentPlanError(
                "the complete equilateral height request is required"
            )
        return BaseHeightTriangle("side_to_height", target[1], raw)
    prefix = re.match(
        r"[ВB] равностороннем треугольнике ABC высота ([ABC])H равна\s*", given
    )
    if prefix:
        raw, rest = _value(given[prefix.end() :])
        if rest.strip(" .") or not re.fullmatch(
            r"\s*стороны этого треугольника\.\s*", request
        ):
            raise ContentPlanError("the complete equilateral side request is required")
        return BaseHeightTriangle("height_to_side", prefix[1], raw)
    return None


def read_question(html, source):
    try:
        text = _text(html, source)
        if text.count("Найдите") != 1:
            raise ContentPlanError("one complete base-height question is required")
        given, request = text.split("Найдите")
        equilateral = _equilateral(given, request)
        if equilateral is not None:
            return equilateral
        apex, side, rest = _setup(given)
        lengths, trig, height = _facts(rest, side)
        base = "".join(sorted(set("ABC") - {apex}))
        target = re.fullmatch(
            r"\s*угол ([ABC])\s*\.\s*Ответ дайте в градусах\.\s*", request
        )
        if (
            side is not None
            or trig is not None
            or height != apex + "H"
            or set(lengths) != {base, height}
            or target is None
            or target[1] != apex
        ):
            raise ContentPlanError(
                "exactly the base and its apex altitude must determine the requested vertex angle"
            )
        model = BaseHeightTriangle(
            "base_height_to_angle", apex, lengths[base][1], lengths[height][1]
        )
        if model.apex_angle.is_Rational is not True:
            raise ContentPlanError(
                "the base and height must give an exact supported angle in degrees"
            )
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
