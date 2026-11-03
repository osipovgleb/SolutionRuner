"""Exact side, height and circumradius relations for regular triangles."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from . import circumcircle_height_model
from .angle_model import DEGREE
from .incircle_model import _positive

RULES = {
    "circle-circumcircle-trapezoid-height-radius": "trapezoid_height",
    "circle-circumcircle-trapezoid-leg-perimeter-midline": "trapezoid_leg",
    "circle-circumcircle-trapezoid-radius-sixty": "trapezoid_radius",
    "circle-circumcircle-regular-polygon-vertices": "polygon_vertices",
    "circle-circumcircle-right-radius-hypotenuse": "right_radius",
    "circle-circumcircle-right-hypotenuse-radius": "right_hypotenuse",
    "circle-circumcircle-right-radius-legs": "right_legs",
    "circle-circumcircle-isosceles-diameter-120": "isosceles_diameter",
    "circle-circumcircle-hexagon-side-radius": "hexagon_side",
    "circle-circumcircle-hexagon-diameter-perimeter": "hexagon_diameter",
    "circle-circumcircle-sine-radius-30": "sine_radius",
    "circle-circumcircle-sine-radius-150": "sine_radius",
    "circle-circumcircle-sine-side": "sine_side",
    "circle-circumcircle-equilateral-radius-side": "radius_side",
    "circle-circumcircle-equilateral-side-radius": "side_radius",
    "circle-circumcircle-equilateral-radius-height": "radius_height",
    "circle-circumcircle-equilateral-height-radius": "height_radius",
}
PATTERNS = {
    "trapezoid_leg": r"Около трапеции описана окружность\.\s*Периметр трапеции равен\s+(.+?)\s*,\s*средняя линия равна\s+(.+?)\s*\.\s*Найдите боковую сторону трапеции\s*\.",
    "trapezoid_radius": rf"Боковая сторона равнобедренной трапеции равна ее меньшему основанию, угол при основании равен\s+(.+?)\s*{DEGREE}\s*,\s*большее основание равно\s+(.+?)\s*\.\s*Найдите радиус описанной окружности этой трапеции\s*\.",
    "polygon_vertices": rf"Угол между двумя соседними сторонами правильного многоугольника, вписанного в окружность, равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите число вершин многоугольника\s*\.",
    "right_radius": r"Гипотенуза прямоугольного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус описанной окружности этого треугольника\s*\.",
    "right_hypotenuse": r"Радиус окружности, описанной около прямоугольного треугольника, равен\s+(.+?)\s*\.\s*Найдите гипотенузу этого треугольника\s*\.",
    "right_legs": rf"[ВB] треугольнике ABC\s+(?:(?:сторона|стороны)\s+)?AC\s*=\s*(.+?)\s*,\s*BC\s*=\s*(.+?)\s*,\s*угол C равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите радиус описанной окружности этого треугольника\s*\.",
    "right_legs_angle_first": rf"[ВB] треугольнике ABC\s+угол C равен\s+(.+?)\s*{DEGREE}\s*,\s*AC\s*=\s*(.+?)\s*,\s*BC\s*=\s*(.+?)\s*\.\s*Найдите радиус описанной окружности этого треугольника\s*\.",
    "isosceles_diameter": rf"Боковая сторона равнобедренного треугольника равна\s+(.+?)\s*,\s*угол при вершине, противолежащей основанию, равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите диаметр описанной окружности этого треугольника\s*\.",
    "hexagon_side": r"Чему равна сторона правильного шестиугольника, вписанного в окружность, радиус которой равен\s+(.+?)\s*\?",
    "hexagon_diameter": r"Периметр правильного шестиугольника равен\s+(.+?)\s*\.\s*Найдите диаметр описанной окружности\s*\.",
    "sine_radius": rf"Сторона AB треугольника ABC\s+равна\s+(.+?)\s*\.\s*Противолежащий ей угол C равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите радиус окружности, описанной около этого треугольника\s*\.",
    "sine_side": rf"Угол C треугольника ABC\s*,\s*вписанного в окружность радиуса\s+(.+?)\s*,\s*равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите сторону AB этого треугольника\s*\.",
    "radius_side": r"Сторона правильного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус окружности, описанной около этого треугольника\s*\.",
    "side_radius": r"Радиус окружности, описанной около правильного треугольника, равен\s+(.+?)\s*\.\s*Найдите сторону этого треугольника\s*\.",
    "radius_height": r"Высота правильного треугольника равна\s+(.+?)\s*\.\s*Найдите радиус окружности, описанной около этого треугольника\s*\.",
    "height_radius": r"Радиус окружности, описанной около правильного треугольника, равен\s+(.+?)\s*\.\s*Найдите высоту этого треугольника\s*\.",
}
FORMULAS = {
    "trapezoid_leg": lambda v: v[0] / 2 - v[1],
    "trapezoid_radius": lambda v: v[0] / 2,
    "polygon_vertices": lambda v: 360 / (180 - v[0]),
    "right_radius": lambda v: v[0] / 2,
    "right_hypotenuse": lambda v: 2 * v[0],
    "right_legs": lambda v: sp.sqrt(v[0] ** 2 + v[1] ** 2) / 2,
    "isosceles_diameter": lambda v: 2 * v[0],
    "hexagon_side": lambda v: v[0],
    "hexagon_diameter": lambda v: v[0] / 3,
    "sine_radius": lambda v: v[0] / (2 * sp.sin(sp.pi * v[1] / 180)),
    "sine_side": lambda v: 2 * v[0] * sp.sin(sp.pi * v[1] / 180),
    "radius_side": lambda v: v[0] / sp.sqrt(3),
    "side_radius": lambda v: v[0] * sp.sqrt(3),
    "radius_height": lambda v: 2 * v[0] / 3,
    "height_radius": lambda v: 3 * v[0] / 2,
}


@dataclass(frozen=True)
class CircumcircleQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def read_question(html, source=None):
    try:
        text = _text(
            circumcircle_height_model.condition_html(html),
            source,
            labels="ABCHORah",
            extra_identifiers=("ABC",),
        ).replace("ё", "е")
        height = circumcircle_height_model.read(text, source)
        if height is not None:
            given, answer = height
            return CircumcircleQuantity("trapezoid_height", given, answer)
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                given = tuple(_positive(v) for v in match.groups())
                if mode == "trapezoid_leg" and given[0] <= 2 * given[1]:
                    raise ContentPlanError(
                        "the cyclic trapezoid must have positive legs"
                    )
                if mode == "trapezoid_radius":
                    given = given[::-1]
                    if given[1] != 60:
                        raise ContentPlanError(
                            "the reviewed trapezoid diameter proof requires a 60-degree base angle"
                        )
                if mode == "polygon_vertices":
                    if given[0] >= 180:
                        raise ContentPlanError(
                            "a regular-polygon interior angle must be below 180"
                        )
                    n = sp.simplify(FORMULAS[mode](given))
                    if n.is_Integer is not True or n < 3:
                        raise ContentPlanError(
                            "the regular polygon must have an integral number of at least three vertices"
                        )
                if mode == "right_legs_angle_first":
                    given, mode = given[1:] + given[:1], "right_legs"
                if mode == "right_legs" and given[2] != 90:
                    raise ContentPlanError(
                        "the reviewed legs method requires angle C=90"
                    )
                if mode == "isosceles_diameter" and given[1] != 120:
                    raise ContentPlanError(
                        "the reviewed isosceles construction requires apex 120"
                    )
                if mode in {"sine_radius", "sine_side"} and given[1] not in {
                    30,
                    45,
                    60,
                    90,
                    120,
                    135,
                    150,
                }:
                    raise ContentPlanError(
                        "the reviewed sine method requires an exact standard angle"
                    )
                return CircumcircleQuantity(
                    mode, given, sp.simplify(FORMULAS[mode](given))
                )
    except (AltitudeSolveError, UnsupportedCondition) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed circumcircle question is required")
