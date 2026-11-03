"""Angles and side lengths determined by the parent's linear identities."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_solver import _parse_positive_value

RULES = {
    "parallelogram-angle-sum": "angle_sum",
    "parallelogram-angle-difference": "angle_difference",
    "parallelogram-diagonal-split-angle": "angle_split",
    "parallelogram-perimeter-side-difference": "side_difference",
    "parallelogram-angle-ratio": "angle_ratio",
    "parallelogram-perimeter-side-ratio": "side_ratio",
}
DEGREE = r"(?:°|\^\{?\\circ\}?)"
ENDING = r"\s*\.\s*Ответ дайте в градусах\s*\."
PATTERNS = {
    "angle_sum": rf"Сумма двух углов параллелограмма равна\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите один из оставшихся углов{ENDING}",
    "angle_difference": rf"Один угол параллелограмма больше другого на\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите больший угол{ENDING}",
    "angle_split": rf"Диагональ параллелограмма образует с двумя его сторонами углы\s+(.+?)\s*{DEGREE}\s+и\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите больший угол параллелограмма{ENDING}",
    "angle_ratio": rf"Найдите больший угол параллелограмма, если два его угла относятся как\s+(.+?)\s*(?::|\\colon)\s*(.+?){ENDING}",
    "side_difference": r"Периметр параллелограмма равен\s+(.+?)\s*\.\s*Одна сторона параллелограмма на\s+(.+?)\s+больше другой\s*\.\s*Найдите меньшую сторону параллелограмма\s*\.",
    "side_known": r"Периметр параллелограмма равен\s+(.+?)\s*\.\s*Меньшая сторона равна\s+(.+?)\s*\.\s*Найдите большую сторону параллелограмма\s*\.",
    "side_ratio": r"Две стороны параллелограмма относятся как\s+(.+?)\s*(?::|\\colon)\s*(.+?)\s*,\s*а периметр его равен\s+(.+?)\s*\.\s*Найдите большую сторону параллелограмма\s*\.",
}


@dataclass(frozen=True)
class LinearQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    first: sp.Expr
    second: sp.Expr
    answer: sp.Expr


def _angles(mode, given):
    if mode == "angle_sum":
        first = given[0] / 2
        if given[0] == 180:
            raise ContentPlanError(
                "a sum of 180 degrees does not identify the remaining angles"
            )
    elif mode == "angle_difference":
        first = (180 - given[0]) / 2
    elif mode == "angle_split":
        first = sum(given)
    else:
        small, large = sorted(given)
        if small == large:
            raise ContentPlanError("equal unspecified angles need not be adjacent")
        first = 180 * small / (small + large)
    if not 0 < first < 180:
        raise ContentPlanError("nondegenerate parallelogram angles are required")
    second = 180 - first
    answer = second if mode == "angle_sum" else max(first, second)
    return LinearQuantity(mode, given, first, second, answer)


def _sides(mode, given):
    if mode == "side_difference":
        perimeter, difference = given
        first = perimeter / 4 - difference / 2
        second = first + difference
    elif mode == "side_known":
        perimeter, first = given
        second = perimeter / 2 - first
    else:
        small, large = sorted(given[:2])
        if small == large:
            raise ContentPlanError("two unspecified equal sides need not be adjacent")
        scale = given[2] / (2 * (small + large))
        first, second = small * scale, large * scale
    if not 0 < first <= second:
        raise ContentPlanError(
            "the claimed smaller side must be positive and no larger than the other"
        )
    answer = first if mode == "side_difference" else second
    return LinearQuantity(mode, given, first, second, answer)


def read_text(text):
    for mode, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            given = tuple(_parse_positive_value(v) for v in match.groups())
            return (
                _angles(mode, given)
                if mode.startswith("angle_")
                else _sides(mode, given)
            )
    raise ContentPlanError(
        "one complete reviewed parallelogram or rhombus question is required"
    )
