"""Parse and validate supported right-triangle condition text."""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction
from html import unescape

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)


def _plain_html(value: str) -> str:
    """Return Unicode-normalized visible text for deterministic rule matching."""

    normalized = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", normalized)).strip()


def _latin_triangle_labels(value: str) -> str:
    """Normalize visually identical Cyrillic triangle labels to Latin names."""

    return value.translate(str.maketrans({"А": "A", "В": "B", "С": "C"}))


def _integer_match(pattern: str, value: str, error: str) -> int:
    """Return one positive integer captured from visible condition text."""

    match = re.search(pattern, value, re.IGNORECASE)
    if match is None:
        raise RightTrianglePlanError(error)
    parsed = int(match.group(1))
    if parsed <= 0:
        raise RightTrianglePlanError(error)
    return parsed


def _acute_angle_ratio(condition_html: str) -> Fraction:
    """Extract the exact larger-to-smaller acute-angle ratio."""

    formulas = re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
    fractions = [
        Fraction(int(match.group(1)), int(match.group(2)))
        for value in formulas
        if (match := re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value)) is not None
    ]
    if len(fractions) > 1:
        raise RightTrianglePlanError("condition must give one acute-angle ratio")
    if fractions:
        return fractions[0]
    visible = _plain_html(condition_html)
    return Fraction(
        _integer_match(
            r"\bв\s+(\d+)\s+раз(?:а)?\s+больше",
            visible,
            "condition must give one acute-angle ratio",
        ),
        1,
    )


def _condition_degree_values(condition_html: str) -> list[int]:
    """Return stated degree values in source order across text and formula spans."""

    return [
        int(value)
        for value in re.findall(
            r"(\d+)(?:\s*°|\^\{?\\circ\}?)",
            _math_aware_html(condition_html),
        )
    ]


def _math_aware_html(value: str) -> str:
    """Return visible text with inline formula attributes restored in place."""

    normalized = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    normalized = re.sub(
        r'<span[^>]*data-inline-latex="([^"]*)"[^>]*>.*?</span>',
        lambda match: match.group(1),
        normalized,
        flags=re.DOTALL,
    )
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", normalized)).strip()


def _acute_condition_angles(condition_html: str) -> list[int]:
    """Return the positive non-right degree values declared by one condition."""

    angles = [
        value for value in _condition_degree_values(condition_html) if value != 90
    ]
    if not angles or any(value <= 0 or value >= 90 for value in angles):
        raise RightTrianglePlanError("condition must give acute angle values")
    return angles


def _require_condition_terms(condition_html: str, *terms: str) -> str:
    """Return visible text after validating every required Russian word stem."""

    visible = _math_aware_html(condition_html)
    lowered = visible.lower()
    if any(term not in lowered for term in terms):
        raise RightTrianglePlanError(
            "condition does not match the registered angle rule"
        )
    return visible


def _single_acute_angle(condition_html: str) -> int:
    """Return the only non-right degree value in one strict condition."""

    angles = _acute_condition_angles(condition_html)
    if len(angles) != 1:
        raise RightTrianglePlanError(
            "condition must give exactly one acute angle value"
        )
    return angles[0]


def _single_line_angle(condition_html: str) -> int:
    """Return one stated angle between lines, allowing the coincident case zero."""

    angles = [
        value for value in _condition_degree_values(condition_html) if value != 90
    ]
    if len(angles) != 1 or angles[0] < 0 or angles[0] >= 45:
        raise RightTrianglePlanError(
            "condition must give one line angle below 45 degrees"
        )
    return angles[0]


def _angle_a_and_hypotenuse(condition_html: str) -> tuple[int, int, bool, str]:
    """Extract angle A and a restricted exact AB value from an altitude task."""

    visible = _latin_triangle_labels(_math_aware_html(condition_html))
    lowered = visible.lower()
    combined = visible.replace(" ", "").replace(r"\quad", "").replace(r"\,", "")
    if "уголcравен90" not in lowered.replace(" ", "") and "90" not in combined:
        raise RightTrianglePlanError("condition must declare right angle C")
    angles = _acute_condition_angles(condition_html)
    if len(angles) != 1 or angles[0] not in {30, 60}:
        raise RightTrianglePlanError(
            "condition must give angle A equal to 30 or 60 degrees"
        )
    radical = re.search(r"AB=(\d*)\\sqrt\{?3\}?", combined)
    if radical is not None:
        coefficient = int(radical.group(1) or "1")
        return (
            angles[0],
            coefficient,
            True,
            (("" if coefficient == 1 else str(coefficient)) + r"\sqrt{3}"),
        )
    plain = re.search(r"AB=(\d+)(?:[,.](\d+))?", combined)
    if plain is None or plain.group(2) is not None:
        raise RightTrianglePlanError("condition must give an exact supported AB value")
    value = int(plain.group(1))
    return angles[0], value, False, str(value)
