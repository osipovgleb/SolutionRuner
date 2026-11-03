"""Rhombus diagonal angles and the side identities from parallelogram bisectors."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_solver import _parse_positive_value
from .linear_model import DEGREE, ENDING, LinearQuantity

RULES = {
    "parallelogram-bisector-side-ratio": "bisector_ratio",
    "parallelogram-adjacent-bisectors-side": "bisector_double",
    "rhombus-full-angle-diagonal": "rhombus_angle",
    "rhombus-diagonal-angle-full": "rhombus_angle",
}
PATTERNS = {
    "bisector_ratio": r"Биссектриса тупого угла параллелограмма делит противоположную сторону в отношении\s+(.+?)\s*(?::|\\colon)\s*(.+?)\s*,\s*считая от вершины острого угла\s*\.\s*Найдите большую сторону параллелограмма, если его периметр равен\s+(.+?)\s*\.",
    "bisector_double": r"Точка пересечения биссектрис двух углов параллелограмма, прилежащих к одной стороне, принадлежит противоположной стороне\s*\.\s*Меньшая сторона параллелограмма равна\s+(.+?)\s*\.\s*Найдите его большую сторону\s*\.",
    "rhombus_angle": rf"[ВB] ромбе\s+ABCD\s+угол\s+([ABCD]{{3}})\s+равен\s+(.+?)\s*{DEGREE}\s*;?\s*\.\s*Найдите угол\s+([ABCD]{{3}}){ENDING}",
}


def is_half(name):
    if len(name) != 3 or len(set(name)) != 3 or set(name) - set("ABCD"):
        raise ContentPlanError("one nondegenerate named rhombus angle is required")
    opposite = "CDAB"["ABCD".index(name[1])]
    return opposite in (name[0], name[2])


@dataclass(frozen=True)
class RhombusAngle:
    known: str
    amount: sp.Expr
    target: str
    angle_a: sp.Expr
    mode: str = "rhombus_angle"

    def full(self, vertex):
        return self.angle_a if vertex in "AC" else 180 - self.angle_a

    def angle(self, name):
        return self.full(name[1]) / (2 if is_half(name) else 1)

    @property
    def answer(self):
        return self.angle(self.target)

    @property
    def diagonals(self):
        return tuple(
            sorted(
                {
                    "AC" if name[1] in "AC" else "BD"
                    for name in (self.known, self.target)
                    if is_half(name)
                }
            )
        )


def read_text(text):
    for mode, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if not match:
            continue
        if mode == "rhombus_angle":
            known, raw, target = match.groups()
            amount = _parse_positive_value(raw)
            full = amount * (2 if is_half(known) else 1)
            is_half(target)
            angle_a = full if known[1] in "AC" else 180 - full
            if not 0 < angle_a < 180:
                raise ContentPlanError("nondegenerate rhombus angles are required")
            return RhombusAngle(known, amount, target, angle_a)
        given = tuple(_parse_positive_value(v) for v in match.groups())
        if mode == "bisector_ratio":
            first, second, perimeter = given
            scale = perimeter / (2 * (2 * first + second))
            small, large = first * scale, (first + second) * scale
        else:
            small, large = given[0], 2 * given[0]
        return LinearQuantity(mode, given, small, large, large)
    return None
