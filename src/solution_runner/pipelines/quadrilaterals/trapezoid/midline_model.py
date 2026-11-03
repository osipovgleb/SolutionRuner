"""Exact scalar relations for trapezoid angles, midlines and parallel cuts."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .isosceles_model import DEGREE

RULES = {
    "isosceles-trapezoid-opposite-angle-difference": "angle_difference",
    "trapezoid-midline-small-large-base": "large_base",
    "trapezoid-diagonal-midline-piece": "diagonal_piece",
    "trapezoid-parallel-cut-perimeter": "cut_perimeter",
    "isosceles-trapezoid-height-base-parts-midline": "base_parts",
    "trapezoid-perimeter-legs-midline": "perimeter_midline",
    "trapezoid-diagonal-midpoints-segment": "diagonal_midpoints",
    "isosceles-trapezoid-perpendicular-diagonals-midline": "perpendicular",
}
PATTERNS = {
    "angle_difference": rf"Чему равен больший угол равнобедренной трапеции, если известно, что разность противолежащих углов равна\s+(.+?)\s*{DEGREE}\s*\?\s*Ответ дайте в градусах\s*\.",
    "large_base": r"Средняя линия трапеции равна\s+(.+?)\s*,\s*а меньшее основание равно\s+(.+?)\s*\.\s*Найдите большее основание трапеции\s*\.",
    "diagonal_piece": r"Основания трапеции равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите больший из отрезков, на которые делит среднюю линию этой трапеции одна из ее диагоналей\s*\.",
    "cut_perimeter": r"Прямая, проведенная параллельно боковой стороне трапеции через конец меньшего основания, равного\s+(.+?)\s*,\s*отсекает треугольник, периметр которого равен\s+(.+?)\s*\.\s*Найдите периметр трапеции\s*\.",
    "base_parts": r"Перпендикуляр, опущенный из вершины тупого угла на большее основание равнобедренной трапеции, делит его на части, имеющие длины\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите среднюю линию этой трапеции\s*\.",
    "perimeter_midline": r"Периметр трапеции равен\s+(.+?)\s*,\s*а сумма (?:двух противоположных )?непараллельных сторон равна\s+(.+?)\s*\.\s*Найдите среднюю линию трапеции\s*\.",
    "diagonal_midpoints": r"Основания трапеции равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите отрезок, соединяющий середины диагоналей трапеции\s*\.",
    "perpendicular": r"[ВB] равнобедренной трапеции диагонали перпендикулярны\s*\.\s*Высота трапеции равна\s+(.+?)\s*\.\s*Найдите ее среднюю линию\s*\.",
}


@dataclass(frozen=True)
class MidlineTrapezoid:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def _model(mode, given):
    a = given[0]
    b = given[1] if len(given) == 2 else None
    if mode == "angle_difference":
        if not a < 180:
            raise ContentPlanError("the angle difference must be less than 180 degrees")
        answer = (180 + a) / 2
    elif mode == "large_base":
        if not a > b:
            raise ContentPlanError("the midline must exceed the smaller base")
        answer = 2 * a - b
    elif mode in {"diagonal_piece", "diagonal_midpoints", "base_parts"}:
        if a == b:
            raise ContentPlanError(
                "distinct bases or distinct height parts are required"
            )
        answer = (
            max(a, b) / 2
            if mode == "diagonal_piece"
            else abs(a - b) / 2
            if mode == "diagonal_midpoints"
            else max(a, b)
        )
    elif mode == "cut_perimeter":
        answer = b + 2 * a
    elif mode == "perimeter_midline":
        if not a > b:
            raise ContentPlanError("the perimeter must exceed the sum of the legs")
        answer = (a - b) / 2
    else:
        answer = a
    return MidlineTrapezoid(mode, given, sp.simplify(answer))


def read_question(html, source=None):
    try:
        text = _text(
            html, source, labels="ABCDEFGKMO", extra_identifiers=("ABCD",)
        ).replace("ё", "е")
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                return _model(
                    mode, tuple(_parse_positive_value(v) for v in match.groups())
                )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed trapezoid scalar question is required"
    )
