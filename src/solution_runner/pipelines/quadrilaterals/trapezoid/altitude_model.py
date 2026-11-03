"""Exact right and oblique trapezoids with an altitude and a known sloping side."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .isosceles_model import DEGREE

RULES = {
    "right-trapezoid-bases-angle-area": "right_area",
    "right-trapezoid-bases-area-angle": "right_angle",
    "trapezoid-bases-side-angle-area": "side_area",
    "trapezoid-bases-side-area-angle": "side_angle",
}
PATTERNS = {
    "right_area": rf"Найдите площадь прямоугольной трапеции, основания которой равны\s+(.+?)\s+и\s+(.+?)\s*,\s*большая боковая сторона составляет с основанием угол\s+(.+?)\s*{DEGREE}\s*\.",
    "right_angle": r"Основания прямоугольной трапеции равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Ее площадь равна\s+(.+?)\s*\.\s*Найдите острый угол этой трапеции\s*\.\s*Ответ дайте в градусах\s*\.",
    "side_area": rf"Основания трапеции равны\s+(.+?)\s+и\s+(.+?)\s*,\s*боковая сторона, равная\s+(.+?)\s*,\s*образует с одним из оснований трапеции угол\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите площадь трапеции\s*\.",
    "side_angle": r"Основания трапеции равны\s+(.+?)\s+и\s+(.+?)\s*,\s*боковая сторона равна\s+(.+?)\s*\.\s*Площадь трапеции равна\s+(.+?)\s*\.\s*Найдите острый угол трапеции, прилежащий к данной боковой стороне\s*\.\s*Ответ (?:выразите|дайте) в градусах\s*\.",
}


@dataclass(frozen=True)
class AltitudeTrapezoid:
    mode: str
    given: tuple[sp.Expr, ...]
    small: sp.Expr
    large: sp.Expr
    height: sp.Expr
    offset: sp.Expr

    @property
    def right(self):
        return self.mode in {"right_area", "right_angle"}

    @property
    def projection(self):
        return self.large - self.small if self.right else self.offset

    @property
    def leg(self):
        return sp.sqrt(sp.simplify(self.height**2 + self.projection**2))

    @property
    def sine(self):
        return sp.simplify(self.height / self.leg)

    @property
    def tangent(self):
        return sp.simplify(self.height / self.projection)

    @property
    def angle(self):
        radians = sp.atan(self.tangent) if self.right else sp.asin(self.sine)
        return sp.simplify(180 * radians / sp.pi)

    @property
    def area(self):
        return sp.simplify((self.small + self.large) * self.height / 2)

    @property
    def is_isosceles(self):
        return sp.simplify(2 * self.offset - (self.large - self.small)) == 0

    @property
    def answer(self):
        return self.area if self.mode.endswith("area") else self.angle


def _model(mode, given):
    small, large = sorted(given[:2])
    if not small < large:
        raise ContentPlanError("distinct trapezoid bases are required")
    if mode == "right_area":
        angle = given[2]
        if not 0 < angle < 90:
            raise ContentPlanError("the sloping side must form a strictly acute angle")
        height = (large - small) * sp.tan(sp.pi * angle / 180)
        offset = sp.S.Zero
    elif mode == "right_angle":
        height = 2 * given[2] / (small + large)
        offset = sp.S.Zero
    elif mode == "side_area":
        leg, angle = given[2:]
        if not 0 < angle < 180 or angle == 90:
            raise ContentPlanError("the reviewed sloping side must be nonperpendicular")
        acute = min(angle, 180 - angle)
        height = leg * sp.sin(sp.pi * acute / 180)
        offset = leg * sp.cos(sp.pi * acute / 180)
    else:
        leg, area = given[2:]
        height = 2 * area / (small + large)
        if height >= leg:
            raise ContentPlanError(
                "the requested acute angle requires an altitude shorter than the side"
            )
        offset = sp.sqrt(leg**2 - height**2)
    return AltitudeTrapezoid(
        mode, given, small, large, sp.simplify(height), sp.simplify(offset)
    )


def read_question(html, source=None):
    try:
        text = _text(html, source, labels="ABCDH", extra_identifiers=("ABCD",)).replace(
            "ё", "е"
        )
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                return _model(
                    mode, tuple(_parse_positive_value(v) for v in match.groups())
                )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed trapezoid altitude question is required"
    )
