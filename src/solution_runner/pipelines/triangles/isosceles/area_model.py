"""Read complete area and inverse-side questions with exact isosceles geometry."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle": (
        "side_angle",
        30,
    ),
    "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle": (
        "side_angle",
        150,
    ),
    "isosceles-triangle-27619-area-from-side-and-base": ("side_base", None),
    "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle": (
        "area_angle",
        30,
    ),
    "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle": (
        "area_angle",
        150,
    ),
}
_ANGLE = r"(30|150)(?:°|\^\{\\circ\})\s*;?\."
_AREA_REQUEST = r"\s*Найдите площадь этого треугольника\.\s*"


@dataclass(frozen=True)
class AreaTriangle:
    given_kind: str
    angle: int | None
    first_raw: str
    second_raw: str | None = None
    apex: str = "C"

    @property
    def side(self):
        value = _parse_positive_value(self.first_raw)
        return (
            sp.simplify(2 * sp.sqrt(value))
            if self.given_kind == "area_angle"
            else value
        )

    @property
    def base(self):
        return (
            _parse_positive_value(self.second_raw)
            if self.given_kind == "side_base"
            else sp.simplify(2 * self.side * sp.sin(sp.pi * self.angle / 360))
        )

    @property
    def height(self):
        if self.angle is not None:
            return sp.simplify(self.side * sp.cos(sp.pi * self.angle / 360))
        return sp.sqrt(sp.simplify(self.side**2 - self.base**2 / 4))

    @property
    def area(self):
        if self.angle is not None:
            return sp.simplify(self.side**2 * sp.sin(sp.pi * self.angle / 180) / 2)
        return sp.simplify(self.base * self.height / 2)

    @property
    def answer(self):
        return self.side if self.given_kind == "area_angle" else self.area

    @property
    def topology(self):
        difference = sp.simplify(2 * self.side**2 - self.base**2)
        return (
            0
            if difference == 0
            else 1
            if difference.is_positive is True
            else -1
            if difference.is_negative is True
            else None
        )

    def require_rule(self, rule):
        if RULES.get(rule) != (self.given_kind, self.angle):
            raise ContentPlanError(
                "the complete area question differs from its registered rule"
            )
        return self


def _finish(rest, model):
    if not re.fullmatch(_AREA_REQUEST, rest):
        raise ContentPlanError("the complete triangle area request is required")
    if sp.simplify(model.side * 2 - model.base).is_positive is not True:
        raise ContentPlanError("the base must be shorter than twice the equal side")
    return model


def _named(text):
    match = re.match(
        r"[ВB] равнобедренном треугольнике ABC угол ([ABC]) равен "
        + _ANGLE
        + r"\s*Боковые стороны (AB|BA|AC|CA|BC|CB)\s*=\s*(AB|BA|AC|CA|BC|CB)\s*=\s*",
        text,
    )
    if match is None:
        raise ContentPlanError("the full named area setup must be reviewed")
    apex, degree, first, second = match.groups()
    if set(first) & set(second) != {apex} or set(first + second) != set("ABC"):
        raise ContentPlanError("the given angle must be between the two equal sides")
    raw, rest = _value(text[match.end() :])
    return _finish(
        rest.lstrip(" ."), AreaTriangle("side_angle", int(degree), raw, apex=apex)
    )


def read_question(html, source):
    try:
        text = _text(html, source)
        if text.startswith(("B равнобедренном", "В равнобедренном")):
            return _named(text)
        base = re.match(r"Боковая сторона равнобедренного треугольника равна\s*", text)
        if base:
            side, rest = _value(text[base.end() :])
            match = re.match(r", а основание равно\s*", rest)
            if match is None:
                raise ContentPlanError("one side and one base must be specified")
            b, rest = _value(rest[match.end() :])
            return _finish(rest.lstrip(" ."), AreaTriangle("side_base", None, side, b))
        match = re.match(
            r"Угол при вершине, противолежащей основанию равнобедренного треугольника, равен "
            + _ANGLE,
            text,
        )
        if match is None:
            raise ContentPlanError(
                "the complete isosceles vertex-angle setup is required"
            )
        angle = int(match[1])
        rest = text[match.end() :].strip()
        side = re.match(r"Боковая сторона треугольника равна\s*", rest)
        if side:
            raw, rest = _value(rest[side.end() :])
            return _finish(rest.lstrip(" ."), AreaTriangle("side_angle", angle, raw))
        area = re.match(
            r"Найдите боковую сторону треугольника, если его площадь равна\s*", rest
        )
        if area is None:
            raise ContentPlanError("one complete inverse area request is required")
        raw, rest = _value(rest[area.end() :])
        if rest.strip(" ."):
            raise ContentPlanError("an unreviewed inverse area statement remains")
        return AreaTriangle("area_angle", angle, raw)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
