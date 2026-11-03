"""Exact side, height and circumradius relations for regular triangles."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from .incircle_model import _positive

RULES = {
    "circle-circumcircle-equilateral-radius-side": "radius_side",
    "circle-circumcircle-equilateral-side-radius": "side_radius",
    "circle-circumcircle-equilateral-radius-height": "radius_height",
    "circle-circumcircle-equilateral-height-radius": "height_radius",
}
PATTERNS = {
    "radius_side": r"Сторона правильного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус окружности, описанной около этого треугольника\s*\.",
    "side_radius": r"Радиус окружности, описанной около правильного треугольника, равен\s+(.+?)\s*\.\s*Найдите сторону этого треугольника\s*\.",
    "radius_height": r"Высота правильного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус окружности, описанной около этого треугольника\s*\.",
    "height_radius": r"Радиус окружности, описанной около правильного треугольника, равен\s+(.+?)\s*\.\s*Найдите высоту этого треугольника\s*\.",
}
FORMULAS = {
    "radius_side": lambda a: a / sp.sqrt(3),
    "side_radius": lambda r: r * sp.sqrt(3),
    "radius_height": lambda h: 2 * h / 3,
    "height_radius": lambda r: 3 * r / 2,
}


@dataclass(frozen=True)
class CircumcircleQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def read_question(html, source=None):
    try:
        text = _text(
            html, source, labels="ABCHORah", extra_identifiers=("ABC",)
        ).replace("ё", "е")
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                amount = _positive(match[1])
                return CircumcircleQuantity(
                    mode, (amount,), sp.simplify(FORMULAS[mode](amount))
                )
    except (AltitudeSolveError, UnsupportedCondition) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed circumcircle question is required")
