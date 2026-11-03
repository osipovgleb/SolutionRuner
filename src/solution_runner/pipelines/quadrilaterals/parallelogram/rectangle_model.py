"""Solve complete square and rectangle questions with exact feasible side lengths."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import NUMBER
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError

RULES = {
    "square-diagonal-area": "square",
    "rectangle-area-difference-larger-side": "difference",
    "rectangle-area-ratio-perimeter": "ratio",
    "rectangle-perimeter-area-larger-side": "side",
    "rectangle-perimeter-diagonal-area": "area",
    "rectangle-perimeter-area-diagonal": "diagonal",
}
PATTERNS = {
    "square": rf"Найдите площадь квадрата, если его диагональ равна\s+({NUMBER})\s*\.",
    "difference": rf"Площадь прямоугольника равна\s+({NUMBER})\s*\.\s*Найдите его большую сторону, если она на\s+({NUMBER})\s+больше меньшей стороны\s*\.",
    "ratio": rf"Найдите периметр прямоугольника, если его площадь равна\s+({NUMBER})\s*,\s*а отношение соседних сторон равно\s+({NUMBER})\s*(?::|\\colon)\s*({NUMBER})\s*\.",
    "side": rf"Периметр прямоугольника равен\s+({NUMBER})\s*,\s*а площадь(?: равна)?\s+({NUMBER})\s*\.\s*Найдите большую сторону прямоугольника\s*\.",
    "area": rf"Периметр прямоугольника равен\s+({NUMBER})\s*,\s*а диагональ равна\s+({NUMBER})\s*\.\s*Найдите площадь этого прямоугольника\s*\.",
    "diagonal": rf"Периметр прямоугольника равен\s+({NUMBER})\s*,\s*а площадь(?: равна)?\s+({NUMBER})\s*\.\s*Найдите диагональ этого прямоугольника\s*\.",
}


@dataclass(frozen=True)
class Rectangle:
    mode: str
    given: tuple[sp.Rational, ...]
    a: sp.Expr
    b: sp.Expr

    @property
    def area(self):
        return sp.simplify(self.a * self.b)

    @property
    def perimeter(self):
        return sp.simplify(2 * (self.a + self.b))

    @property
    def diagonal(self):
        return sp.sqrt(sp.simplify(self.a**2 + self.b**2))

    @property
    def answer(self):
        if self.mode in {"square", "area"}:
            return self.area
        if self.mode == "ratio":
            return self.perimeter
        if self.mode == "diagonal":
            return self.diagonal
        return sp.simplify(sp.Max(self.a, self.b))


def _sides(mode, given):
    first = given[0]
    if mode == "square":
        return (first / sp.sqrt(2),) * 2
    second = given[1]
    if mode == "difference":
        small = (sp.sqrt(second**2 + 4 * first) - second) / 2
        return small, small + second
    if mode == "ratio":
        scale = sp.sqrt(first / (second * given[2]))
        return second * scale, given[2] * scale
    total = first / 2
    discriminant = 2 * second**2 - total**2 if mode == "area" else total**2 - 4 * second
    if discriminant < 0:
        raise ContentPlanError("the data admit no real rectangle sides")
    return (total - sp.sqrt(discriminant)) / 2, (total + sp.sqrt(discriminant)) / 2


def read_question(html, source=None):
    try:
        text = _text(html, source, labels="ABCD")
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    for mode, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            given = tuple(
                sp.Rational(v.replace("{,}", ".").replace(",", "."))
                for v in match.groups()
            )
            if any(v <= 0 for v in given):
                raise ContentPlanError("rectangle givens must be positive")
            a, b = _sides(mode, given)
            if min(a, b) <= 0:
                raise ContentPlanError("a nondegenerate rectangle is required")
            return Rectangle(mode, given, a, b)
    raise ContentPlanError(
        "one complete reviewed square or rectangle question is required"
    )
