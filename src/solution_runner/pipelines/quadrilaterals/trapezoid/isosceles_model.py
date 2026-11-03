"""Exact isosceles-trapezoid quantities from the parent's altitude triangle."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "isosceles-trapezoid-bases-leg-sine": "sine",
    "isosceles-trapezoid-bases-cosine-leg": "cosine_leg",
    "isosceles-trapezoid-leg-sine-small-base": "small_sine",
    "isosceles-trapezoid-bases-tangent-height": "tangent_height",
    "isosceles-trapezoid-height-tangent-large-base": "large_tangent",
    "isosceles-trapezoid-bases-height-tangent": "tangent",
    "isosceles-trapezoid-bases-perimeter-area": "perimeter_area",
    "isosceles-trapezoid-bases-area-perimeter": "area",
    "isosceles-trapezoid-bases-leg-area": "side_area",
    "isosceles-trapezoid-bases-area-leg": "area",
    "isosceles-trapezoid-leg-sixty-small-base": "small_sixty",
    "isosceles-trapezoid-bases-sixty-perimeter": "perimeter_sixty",
    "isosceles-trapezoid-bases-fortyfive-height": "height_fortyfive",
}
BASES = r"Основания равнобедренной трапеции равны\s+(.+?)\s+и\s+(.+?)"
DEGREE = r"(?:°|\^\{?\\circ\}?)"
PATTERNS = {
    "sine": BASES
    + r"\s*\.\s*Боковые стороны равны\s+(.+?)\s*\.\s*Найдите синус острого угла трапеции\s*\.",
    "cosine_leg": BASES
    + r"\s*\.\s*Косинус острого угла трапеции равен\s+(.+?)\s*\.?\s*Найдите боковую сторону\s*\.",
    "small_sine": r"Большее основание равнобедренной трапеции равно\s+(.+?)\s*\.\s*Боковая сторона равна\s+(.+?)\s*\.\s*Синус острого угла равен\s+(.+?)\s*\.\s*Найдите меньшее основание\s*\.",
    "tangent_height": BASES
    + r"\s*\.\s*Тангенс острого угла равен\s+(.+?)\s*\.\s*Найдите высоту трапеции\s*\.",
    "large_tangent": r"Меньшее основание равнобедренной трапеции равно\s+(.+?)\s*\.\s*Высота трапеции равна\s+(.+?)\s*\.\s*Тангенс острого угла равен\s+(.+?)\s*\.\s*Найдите большее основание\s*\.",
    "tangent": BASES
    + r"\s*\.\s*Высота трапеции равна\s+(.+?)\s*\.\s*Найдите тангенс острого угла(?: трапеции)?\s*\.",
    "perimeter_area": BASES
    + r"\s*,\s*а ее периметр равен\s+(.+?)\s*\.\s*Найдите площадь трапеции\s*\.",
    "area": BASES
    + r"\s*,\s*а ее площадь равна\s+(.+?)\s*\.\s*Найдите (периметр|боковую сторону) трапеции\s*\.",
    "side_area": BASES
    + r"\s*,\s*а ее боковые стороны равны\s+(.+?)\s*\.\s*Найдите площадь трапеции\s*\.",
    "small_sixty": rf"[ВB] равнобедренной трапеции большее основание равно\s+(.+?)\s*,\s*боковая сторона равна\s+(.+?)\s*,\s*угол между ними\s+60\s*{DEGREE}\s*\.\s*Найдите меньшее основание\s*\.",
    "perimeter_sixty": rf"[ВB] равнобедренной трапеции основания равны\s+(.+?)\s+и\s+(.+?)\s*,\s*острый угол равен\s+60\s*{DEGREE}\s*\.\s*Найдите ее периметр\s*\.",
    "height_fortyfive": BASES
    + rf"\s*,\s*один из углов равен\s+45\s*{DEGREE}\s*\.\s*Найдите высоту трапеции\s*\.",
}


@dataclass(frozen=True)
class IsoTrapezoid:
    mode: str
    given: tuple[sp.Expr, ...]
    small: sp.Expr
    large: sp.Expr
    height: sp.Expr
    requested: str

    @property
    def projection(self):
        return sp.simplify((self.large - self.small) / 2)

    @property
    def leg(self):
        return sp.sqrt(sp.simplify(self.height**2 + self.projection**2))

    @property
    def sine(self):
        return sp.simplify(self.height / self.leg)

    @property
    def cosine(self):
        return sp.simplify(self.projection / self.leg)

    @property
    def tangent(self):
        return sp.simplify(self.height / self.projection)

    @property
    def area(self):
        return sp.simplify((self.large + self.small) * self.height / 2)

    @property
    def perimeter(self):
        return sp.simplify(self.large + self.small + 2 * self.leg)

    @property
    def answer(self):
        return getattr(self, self.requested)


def _height_from_bases(mode, given, small, large):
    projection = (large - small) / 2
    if mode in {"sine", "side_area", "perimeter_area"}:
        leg = given[2] if mode != "perimeter_area" else (given[2] - small - large) / 2
        if leg <= projection:
            raise ContentPlanError("the leg must exceed the positive base projection")
        return sp.sqrt(leg**2 - projection**2)
    if mode == "cosine_leg":
        cosine = given[2]
        if not 0 < cosine < 1:
            raise ContentPlanError("the cosine must belong to a strictly acute angle")
        return projection * sp.sqrt(1 - cosine**2) / cosine
    if mode in {"perimeter_sixty", "height_fortyfive"}:
        return projection * (sp.sqrt(3) if mode == "perimeter_sixty" else 1)
    amount = given[2]
    return {
        "area": 2 * amount / (small + large),
        "tangent_height": projection * amount,
        "tangent": amount,
    }[mode]


def _model(mode, values):
    requested = values[-1] if mode == "area" else ""
    raw = values[:-1] if mode == "area" else values
    given = tuple(_parse_positive_value(v) for v in raw)
    if mode in {"small_sine", "small_sixty"}:
        large, leg = given[:2]
        sine = given[2] if mode == "small_sine" else sp.sqrt(3) / 2
        if not 0 < sine < 1:
            raise ContentPlanError("the angle must be strictly acute")
        height = leg * sine
        small = large - 2 * leg * sp.sqrt(1 - sine**2)
    elif mode == "large_tangent":
        small, height, tangent = given
        large = small + 2 * height / tangent
    else:
        small, large = sorted(given[:2])
        height = _height_from_bases(mode, given, small, large)
    small, large, height = map(sp.simplify, (small, large, height))
    if not 0 < small < large or height <= 0:
        raise ContentPlanError(
            "distinct positive bases and a positive altitude are required"
        )
    target = {
        "sine": "sine",
        "cosine_leg": "leg",
        "small_sine": "small",
        "tangent_height": "height",
        "large_tangent": "large",
        "tangent": "tangent",
        "perimeter_area": "area",
        "side_area": "area",
        "small_sixty": "small",
        "perimeter_sixty": "perimeter",
        "height_fortyfive": "height",
    }
    target["area"] = "perimeter" if requested == "периметр" else "leg"
    return IsoTrapezoid(mode, given, small, large, height, target[mode])


def read_question(html, source=None):
    try:
        text = (
            _text(html, source, labels="ABCDEH", extra_identifiers=("ABCD",))
            .replace("ё", "е")
            .replace("\u0301", "")
        )
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                return _model(mode, match.groups())
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed isosceles-trapezoid question is required"
    )
