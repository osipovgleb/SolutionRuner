"""Parse universal right-triangle conditions and trigonometric requests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_conditions import _latin_triangle_labels, _plain_html


@dataclass(frozen=True)
class UniversalRightTriangleValues:
    """Hold one condition normalized to side roles around an acute angle."""

    right_angle: str
    trig_name: str
    trig_angle: str
    trig_latex: str
    known_side: str
    known_latex: str
    requested_side: str
    hypotenuse: str
    numerator_side: str
    denominator_side: str


@dataclass(frozen=True)
class UniversalTrigRequestValues:
    """Hold a condition that asks for a trig value from two known sides."""

    right_angle: str
    trig_name: str
    trig_angle: str
    known_sides: tuple[tuple[str, str], tuple[str, str]]
    hypotenuse: str
    numerator_side: str
    denominator_side: str


def _opposite_side(vertex: str) -> str:
    """Return the side opposite one ABC vertex."""

    return {"A": "BC", "B": "AC", "C": "AB"}[vertex]


def _normalized_trig_formula(value: str) -> str:
    """Normalize supported source aliases to the project's sin/cos/tg/ctg names."""

    normalized = _latin_triangle_labels(value).replace(" ", "")
    return (
        normalized.replace(r"\operatorname{tg}", r"\tg")
        .replace(r"\operatorname{ctg}", r"\ctg")
        .replace(r"\tan", r"\tg")
        .replace(r"\cot", r"\ctg")
    )


def _right_angle_labels(visible: str, values: list[str]) -> list[str]:
    """Return the declared right-angle label across supported source layouts."""

    direct = re.findall(r"угол\s+([ABC])\s+равен\s+90", visible, re.IGNORECASE)
    if direct:
        return [label.upper() for label in direct]
    if any(re.fullmatch(r"90(?:\^\{?\\circ\}?)?", value) for value in values):
        split = re.findall(r"угол\s+([ABC])\s+равен\b", visible, re.IGNORECASE)
        if split:
            return [label.upper() for label in split]
    return [
        match.group(1).upper()
        for value in values
        if (
            match := re.fullmatch(
                r"(?:\\angle)?([ABC])=90(?:\^\{?\\circ\}?)?",
                value,
            )
        )
        is not None
    ]


def _universal_values(condition_html: str) -> UniversalRightTriangleValues:
    """Extract and normalize one right-angle, trig value, side, and request."""

    values = [
        _normalized_trig_formula(value)
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
    ]
    trig_values: list[tuple[str, str, str]] = []
    known_values: list[tuple[str, str]] = []
    for value in values:
        trig = re.fullmatch(r"\\(sin|cos|tg|ctg)([ABC])=(.+)", value)
        if trig is not None:
            trig_values.append((trig.group(1), trig.group(2), trig.group(3)))
            continue
        known = re.fullmatch(r"(AB|AC|BC)=(.+)", value)
        if known is not None:
            known_values.append((known.group(1), known.group(2)))

    visible = _latin_triangle_labels(_plain_html(condition_html))
    if not known_values:
        plain_known = re.search(
            r"\b(AB|AC|BC)\s*=\s*(\d+(?:[,.]\d+)?)",
            visible,
        )
        if plain_known is not None:
            known_values.append(
                (
                    plain_known.group(1),
                    plain_known.group(2).replace(",", "{,}"),
                )
            )
    right = _right_angle_labels(visible, values)
    requested_match = re.search(r"Найдите\s+(AB|AC|BC)\b", visible, re.IGNORECASE)
    latex_requested = next(
        (value for value in values if value in {"AB", "AC", "BC"}), None
    )
    requested = (
        requested_match.group(1) if requested_match is not None else latex_requested
    )
    if len(right) != 1:
        raise RightTrianglePlanError("condition must declare one right angle")
    if len(trig_values) != 1:
        raise RightTrianglePlanError(
            "condition must declare one sin, cos, tg, or ctg value"
        )
    if len(known_values) != 1:
        raise RightTrianglePlanError("condition must declare one known side")
    if requested is None:
        raise RightTrianglePlanError("condition must request AB, AC, or BC")

    right_angle = right[0].upper()
    trig_name, trig_angle, trig_latex = trig_values[0]
    known_side, known_latex = known_values[0]
    requested = requested.upper()
    if trig_angle == right_angle:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    if known_side == requested:
        raise RightTrianglePlanError("known and requested sides must differ")

    hypotenuse = _opposite_side(right_angle)
    opposite = _opposite_side(trig_angle)
    if opposite == hypotenuse:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    adjacent_candidates = {"AB", "AC", "BC"} - {hypotenuse, opposite}
    if len(adjacent_candidates) != 1:
        raise RightTrianglePlanError("right-triangle side roles are ambiguous")
    adjacent = adjacent_candidates.pop()
    numerator_side, denominator_side = {
        "sin": (opposite, hypotenuse),
        "cos": (adjacent, hypotenuse),
        "tg": (opposite, adjacent),
        "ctg": (adjacent, opposite),
    }[trig_name]
    return UniversalRightTriangleValues(
        right_angle=right_angle,
        trig_name=trig_name,
        trig_angle=trig_angle,
        trig_latex=trig_latex,
        known_side=known_side,
        known_latex=known_latex,
        requested_side=requested,
        hypotenuse=hypotenuse,
        numerator_side=numerator_side,
        denominator_side=denominator_side,
    )


def _universal_trig_request_values(
    condition_html: str,
) -> UniversalTrigRequestValues | None:
    """Extract a request for one trig value from exactly two known sides."""

    values = [
        _normalized_trig_formula(value)
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
    ]
    requested = [
        (match.group(1), match.group(2))
        for value in values
        if (match := re.fullmatch(r"\\(sin|cos|tg|ctg)([ABC])", value)) is not None
    ]
    if not requested:
        return None
    known = [
        (match.group(1), match.group(2))
        for value in values
        if (match := re.fullmatch(r"(AB|AC|BC)=(.+)", value)) is not None
    ]
    visible = _latin_triangle_labels(_plain_html(condition_html))
    right = _right_angle_labels(visible, values)
    if len(right) != 1:
        raise RightTrianglePlanError("condition must declare one right angle")
    if len(requested) != 1:
        raise RightTrianglePlanError(
            "condition must request one sin, cos, tg, or ctg value"
        )
    if len(known) != 2 or len({side for side, _ in known}) != 2:
        raise RightTrianglePlanError(
            "trig request must declare two distinct known sides"
        )

    right_angle = right[0].upper()
    trig_name, trig_angle = requested[0]
    if trig_angle == right_angle:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    hypotenuse = _opposite_side(right_angle)
    opposite = _opposite_side(trig_angle)
    if opposite == hypotenuse:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    adjacent = ({"AB", "AC", "BC"} - {hypotenuse, opposite}).pop()
    numerator_side, denominator_side = {
        "sin": (opposite, hypotenuse),
        "cos": (adjacent, hypotenuse),
        "tg": (opposite, adjacent),
        "ctg": (adjacent, opposite),
    }[trig_name]
    return UniversalTrigRequestValues(
        right_angle=right_angle,
        trig_name=trig_name,
        trig_angle=trig_angle,
        known_sides=(known[0], known[1]),
        hypotenuse=hypotenuse,
        numerator_side=numerator_side,
        denominator_side=denominator_side,
    )


def _latex_values(condition_html: str) -> tuple[str, str, str, str, str]:
    """Extract one trig value plus the exact known/requested side rule."""

    values = re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
    trig_values = [
        (name, value.removeprefix(prefix))
        for name, prefix in (
            ("sin", r"\sin A="),
            ("cos", r"\cos A="),
            ("tg", r"\tg A="),
        )
        for value in values
        if value.startswith(prefix)
    ]
    known = next(
        (value for value in values if value.startswith(("AC=", "AB="))),
        None,
    )
    visible = _plain_html(condition_html)
    visible = re.sub(r"\bАС\b", "AC", visible)
    visible = re.sub(r"\bАВ\b", "AB", visible)
    if known is None:
        plain_side = re.search(r"\b(AC|AB)\s*=\s*(\d+(?:[,.]\d+)?)", visible)
        if plain_side is not None:
            known = f"{plain_side.group(1)}={plain_side.group(2).replace(',', '{,}')}"
    requested_match = re.search(r"Найдите\s+(AC|AB|BC)\b", visible)
    latex_requested = next(
        (value for value in values if value in {"AC", "AB", "BC"}),
        None,
    )
    if len(trig_values) != 1 or known is None:
        raise RightTrianglePlanError(
            "condition must declare one sin A, cos A, or tg A and a known side"
        )
    requested = (
        requested_match.group(1) if requested_match is not None else latex_requested
    )
    if requested is None:
        raise RightTrianglePlanError("condition must request AC, AB, or BC")
    known_side = known[:2]
    return (
        trig_values[0][0],
        trig_values[0][1],
        known_side,
        known.removeprefix("AC=").removeprefix("AB="),
        requested,
    )
