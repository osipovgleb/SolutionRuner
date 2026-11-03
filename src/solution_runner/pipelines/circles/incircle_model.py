"""Exact area and triangle-radius relations with certified existence checks."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from . import incircle_quad_model
from .angle_model import DEGREE

RULES = {
    "circle-incircle-trapezoid-midline-legs": "trapezoid_legs",
    "circle-incircle-trapezoid-midline-perimeter": "trapezoid_perimeter",
    "circle-incircle-right-trapezoid-radius": "right_trapezoid_radius",
    "circle-incircle-quadrilateral-perimeter": "tangential_quad",
    "circle-incircle-quadrilateral-larger-side": "tangential_quad",
    "circle-incircle-quadrilateral-fourth-side": "tangential_quad",
    "circle-incircle-quadrilateral-opposite-side": "tangential_quad",
    "circle-incircle-three-tangent-cuts": "tangent_cuts",
    "circle-incircle-rhombus-radius": "rhombus_radius",
    "circle-incircle-rhombus-side": "rhombus_side",
    "circle-incircle-hexagon-radius": "hexagon_radius",
    "circle-incircle-hexagon-side": "hexagon_side",
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
    **incircle_quad_model.PATTERNS,
    "trapezoid_legs": r"Боковые стороны трапеции, описанной около окружности, равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите среднюю линию трапеции\s*\.",
    "trapezoid_perimeter": r"Около окружности описана трапеция, периметр которой равен\s+(.+?)\s*\.\s*Найдите длину ее средней линии\s*\.",
    "right_trapezoid_radius": r"Периметр прямоугольной трапеции, описанной около окружности, равен\s+(.+?)\s*,\s*ее большая боковая сторона равна\s+(.+?)\s*\.\s*Найдите радиус окружности\s*\.",
    "tangent_cuts": r"К окружности, вписанной в треугольник ABC\s*,\s*проведены три касательные\s*\.\s*Периметры отсеченных треугольников равны\s+(.+?)\s*,\s+(.+?)\s*,\s+(.+?)\s*\.\s*Найдите периметр данного треугольника\s*\.",
    "rhombus_radius": rf"Сторона ромба равна\s+(.+?)\s*,\s*острый угол равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите радиус вписанной окружности этого ромба\s*\.",
    "rhombus_side": rf"Острый угол ромба равен\s+(.+?)\s*{DEGREE}\s*\.\s*Радиус вписанной в этот ромб окружности равен\s+(.+?)\s*\.\s*Найдите сторону ромба\s*\.",
    "hexagon_side": r"Найдите сторону правильного шестиугольника, описанного около окружности, радиус которой равен\s+(.+?)\s*\.",
    "hexagon_radius": r"Найдите радиус окружности, вписанной в правильный шестиугольник со стороной\s+(.+?)\s*\.",
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
    "trapezoid_legs": lambda v: sum(v) / 2,
    "trapezoid_perimeter": lambda v: v[0] / 4,
    "right_trapezoid_radius": lambda v: (v[0] / 2 - v[1]) / 2,
    "tangent_cuts": lambda v: sum(v),
    "rhombus_radius": lambda v: v[0] / 4,
    "rhombus_side": lambda v: 4 * v[1],
    "hexagon_side": lambda v: 2 * v[0] / sp.sqrt(3),
    "hexagon_radius": lambda v: v[0] * sp.sqrt(3) / 2,
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
    "right_trapezoid_radius": lambda v: v[0] / 4 < v[1] < v[0] / 2,
    "rhombus_radius": lambda v: v[1] == 30,
    "rhombus_side": lambda v: v[0] == 30,
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
    target: str = ""


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
            html,
            source,
            labels="ABCDHKNOSPrpah",
            extra_identifiers=("ABC", "ABCD", "AC", "BC"),
        ).replace("ё", "е")
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if not match:
                continue
            given = tuple(_positive(v) for v in match.groups())
            if mode in incircle_quad_model.PATTERNS:
                return IncircleQuantity(
                    "tangential_quad",
                    given,
                    incircle_quad_model.solve(mode, given),
                    mode,
                )
            if mode in CONSTRAINTS and not CONSTRAINTS[mode](given):
                raise ContentPlanError(
                    "the angle differs from the reviewed incircle method"
                    if mode in {"rhombus_radius", "rhombus_side", "right_radius"}
                    else "the given incircle data do not describe a nondegenerate figure"
                )
            return IncircleQuantity(mode, given, sp.simplify(FORMULAS[mode](given)))
    except (AltitudeSolveError, UnsupportedCondition) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed incircle question is required")
