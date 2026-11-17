"""Build exact solution rows for right-triangle problems."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from html import unescape

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_conditions import (
    _acute_angle_ratio,
    _integer_match,
    _plain_html,
)
from .planner_notation import _answer_text


def _leg_hypotenuse_area_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve an area request from one leg and the hypotenuse."""

    visible = _plain_html(condition_html)
    match = re.search(
        r"катет\s+и\s+гипотенуза\s+равны\s+соответственно\s+(\d+)\s+и\s+(\d+)",
        visible,
        re.IGNORECASE,
    )
    if match is None or "найдите площадь" not in visible.lower():
        raise RightTrianglePlanError(
            "condition must give one leg and the hypotenuse and request area"
        )
    leg, hypotenuse = map(int, match.groups())
    other_square = hypotenuse * hypotenuse - leg * leg
    other_leg = math.isqrt(other_square)
    if leg <= 0 or hypotenuse <= leg or other_leg * other_leg != other_square:
        raise RightTrianglePlanError("condition must determine an integer second leg")
    area = Fraction(leg * other_leg, 2)
    answer = _answer_text(float(area))
    return answer, [
        rf"b=\sqrt{{{hypotenuse}^{{2}}-{leg}^{{2}}}}={other_leg}",
        rf"S=\frac{{1}}{{2}}\cdot{leg}\cdot{other_leg}={answer.replace(',', '{,}')}",
    ]


def _area_leg_difference_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the smaller-leg request from area and an integer leg difference."""

    visible = _plain_html(condition_html)
    if "найдите меньший катет" not in visible.lower():
        raise RightTrianglePlanError("condition must request the smaller leg")
    area = _integer_match(
        r"площадь\s+прямоугольного\s+треугольника\s+равна\s+(\d+)",
        visible,
        "condition must give an integer area",
    )
    difference = _integer_match(
        r"катетов\s+на\s+(\d+)\s+больше",
        visible,
        "condition must give an integer leg difference",
    )
    discriminant = difference * difference + 8 * area
    root = math.isqrt(discriminant)
    if root * root != discriminant or (root - difference) % 2:
        raise RightTrianglePlanError("condition must determine an integer smaller leg")
    positive = (root - difference) // 2
    negative = -(root + difference) // 2
    if positive <= 0:
        raise RightTrianglePlanError("condition must determine a positive smaller leg")
    formula = (
        rf"\frac{{1}}{{2}}x(x+{difference})={area}"
        rf"\iff x(x+{difference})={2 * area}"
        rf"\iff x^{{2}}+{difference}x-{2 * area}=0"
        rf"\iff \begin{{cases}}\left[\begin{{aligned}}x={positive}\\x={negative}"
        rf"\end{{aligned}}\right.\\x\gt 0\end{{cases}}\iff x={positive}"
    )
    return str(positive), [formula]


def _acute_angle_difference_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the larger acute angle from the stated integer difference."""

    visible = _plain_html(condition_html)
    if "найдите больший острый угол" not in visible.lower():
        raise RightTrianglePlanError("condition must request the larger acute angle")
    visible_difference = re.search(
        r"на\s+(\d+)°\s+больше",
        visible,
        re.IGNORECASE,
    )
    formula_differences = [
        int(match.group(1))
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
        if (match := re.fullmatch(r"(\d+)\^\{\\circ\}", value)) is not None
    ]
    candidates = (
        [int(visible_difference.group(1))]
        if visible_difference is not None
        else formula_differences
    )
    if len(candidates) != 1:
        raise RightTrianglePlanError(
            "condition must give an integer acute-angle difference"
        )
    difference = candidates[0]
    if difference >= 90:
        raise RightTrianglePlanError(
            "acute-angle difference must be less than 90 degrees"
        )
    larger = Fraction(90 + difference, 2)
    smaller = Fraction(90 - difference, 2)
    answer = _answer_text(float(larger))
    larger_latex = answer.replace(",", "{,}")
    smaller_latex = _answer_text(float(smaller)).replace(",", "{,}")
    formula = (
        rf"\begin{{cases}}\angle A-\angle B={difference}^{{\circ}}\\"
        rf"\angle A+\angle B=90^{{\circ}}\end{{cases}}"
        rf"\iff \begin{{cases}}\angle A={larger_latex}^{{\circ}}\\"
        rf"\angle B={smaller_latex}^{{\circ}}\end{{cases}}"
    )
    return answer, [formula]


def _acute_angle_ratio_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the larger acute angle from its exact ratio to the smaller one."""

    visible = _plain_html(condition_html)
    if "найдите больший острый угол" not in visible.lower():
        raise RightTrianglePlanError("condition must request the larger acute angle")
    ratio = _acute_angle_ratio(condition_html)
    if ratio <= 1:
        raise RightTrianglePlanError("larger-to-smaller angle ratio must exceed one")
    larger_coefficient = ratio.numerator
    smaller_coefficient = ratio.denominator
    unit = Fraction(90, larger_coefficient + smaller_coefficient)
    larger = larger_coefficient * unit
    if unit.denominator != 1 or larger.denominator != 1:
        raise RightTrianglePlanError("condition must determine integer acute angles")
    unit_value = unit.numerator
    larger_value = larger.numerator
    return str(larger_value), [
        (
            rf"{smaller_coefficient}x+{larger_coefficient}x=90^{{\circ}}"
            rf"\iff{smaller_coefficient + larger_coefficient}x=90^{{\circ}}"
            rf"\iff x={unit_value}^{{\circ}}"
        ),
        (
            rf"{larger_coefficient}x={larger_coefficient}\cdot{unit_value}^{{\circ}}="
            rf"{larger_value}^{{\circ}}"
        ),
    ]
