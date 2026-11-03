"""Exact area and triangle-radius relations with certified existence checks."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from .angle_model import DEGREE

RULES = {
    "circle-incircle-polygon-area": "polygon_area",
    "circle-incircle-triangle-area": "triangle_area",
    "circle-incircle-triangle-perimeter": "triangle_perimeter",
    "circle-incircle-equilateral-radius-height": "equilateral_radius_height",
    "circle-incircle-equilateral-height-radius": "equilateral_height_radius",
    "circle-incircle-equilateral-radius-side": "equilateral_radius_side",
    "circle-incircle-equilateral-side-radius": "equilateral_side_radius",
    "circle-incircle-isosceles-right-radius": "isosceles_right_radius",
    "circle-incircle-right-triangle-radius": "right_radius",
    "circle-incircle-isosceles-triangle-radius": "isosceles_radius",
    "circle-incircle-isosceles-tangent-perimeter": "tangent_perimeter",
}
PATTERNS = {
    "polygon_area": r"Около окружности, радиус которой равен\s+(.+?)\s*,\s*описан многоугольник, периметр которого равен\s+(.+?)\s*\.\s*Найдите его площадь\s*\.",
    "triangle_area": r"Периметр треугольника равен\s+(.+?)\s*,\s*а радиус вписанной окружности равен\s+(.+?)\s*\.\s*Найдите площадь этого треугольника\s*\.",
    "triangle_perimeter": r"Площадь треугольника равна\s+(.+?)\s*,\s*а радиус вписанной окружности равен\s+(.+?)\s*\.\s*Найдите периметр этого треугольника\s*\.",
    "equilateral_radius_height": r"Найдите радиус окружности, вписанной в правильный треугольник, высота которого равна\s+(.+?)\s*\.",
    "equilateral_height_radius": r"Радиус окружности, вписанной в правильный треугольник, равен\s+(.+?)\s*\.\s*Найдите высоту этого треугольника\s*\.",
    "equilateral_side_radius": r"Радиус окружности, вписанной в правильный треугольник, равен\s+(.+?)\s*\.\s*Найдите сторону этого треугольника\s*\.",
    "equilateral_radius_side": r"Сторона правильного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус окружности, вписанной в этот треугольник\s*\.",
    "isosceles_right_radius": r"Катеты равнобедренного прямоугольного треугольника равны\s+(.+?)\s*\.\s*Найдите радиус окружности, вписанной в этот треугольник\s*\.",
    "right_radius": rf"[ВB] треугольнике ABC\s+(?:стороны|известно, что) AC\s*=\s*(.+?)\s*,\s*BC\s*=\s*(.+?)\s*,\s*угол C\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите радиус вписанной окружности\s*\.",
    "isosceles_radius": r"Боковые стороны равнобедренного треугольника равны\s+(.+?)\s*,\s*основание равно\s+(.+?)\s*\.\s*Найдите радиус вписанной окружности\s*\.",
    "tangent_perimeter": r"Окружность, вписанная в равнобедренный треугольник, делит в точке касания одну из боковых сторон на два отрезка, длины которых равны\s+(.+?)\s+и\s+(.+?)\s*,\s*считая от вершины, противолежащей основанию\s*\.\s*Найдите периметр треугольника\s*\.",
}
FORMULAS = {
    "polygon_area": lambda v: v[0] * v[1] / 2,
    "triangle_area": lambda v: v[0] * v[1] / 2,
    "triangle_perimeter": lambda v: 2 * v[0] / v[1],
    "equilateral_radius_height": lambda v: v[0] / 3,
    "equilateral_height_radius": lambda v: 3 * v[0],
    "equilateral_side_radius": lambda v: 2 * sp.sqrt(3) * v[0],
    "equilateral_radius_side": lambda v: v[0] * sp.sqrt(3) / 6,
    "isosceles_right_radius": lambda v: v[0] * (2 - sp.sqrt(2)) / 2,
    "right_radius": lambda v: (v[0] + v[1] - sp.sqrt(v[0] ** 2 + v[1] ** 2)) / 2,
    "isosceles_radius": lambda v: (
        v[1] * sp.sqrt(v[0] ** 2 - v[1] ** 2 / 4) / (2 * v[0] + v[1])
    ),
    "tangent_perimeter": lambda v: 2 * v[0] + 4 * v[1],
}
CONSTRAINTS = {
    "polygon_area": lambda v: v[1] > 2 * sp.pi * v[0],
    # Heron and AM-GM give p² >= 27r²; these equivalent squared forms are exact.
    "triangle_area": lambda v: v[0] ** 2 >= 108 * v[1] ** 2,
    "triangle_perimeter": lambda v: v[0] ** 2 >= 27 * v[1] ** 4,
    "right_radius": lambda v: v[2] == 90,
    "isosceles_radius": lambda v: 2 * v[0] > v[1],
}


@dataclass(frozen=True)
class IncircleQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def _positive(raw):
    amount = ScalarParser(raw).parse()
    if (
        amount.is_real is not True
        or amount.is_finite is not True
        or amount.is_positive is not True
    ):
        raise ContentPlanError("incircle data must be positive finite real numbers")
    return amount


def read_question(html, source=None):
    try:
        text = _text(
            html, source, labels="ABCHKOSPrpah", extra_identifiers=("ABC", "AC", "BC")
        ).replace("ё", "е")
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if not match:
                continue
            given = tuple(_positive(v) for v in match.groups())
            if mode in CONSTRAINTS and not CONSTRAINTS[mode](given):
                raise ContentPlanError(
                    "the given incircle data do not describe a nondegenerate figure"
                )
            return IncircleQuantity(mode, given, sp.simplify(FORMULAS[mode](given)))
    except (AltitudeSolveError, UnsupportedCondition) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed incircle area or triangle question is required"
    )
