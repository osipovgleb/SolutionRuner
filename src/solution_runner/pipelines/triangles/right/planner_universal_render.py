"""Build normalized right-triangle content transformations."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_notation import (
    _positive_root_latex,
    _trig_square,
)
from .planner_universal_parse import (
    UniversalRightTriangleValues,
    UniversalTrigRequestValues,
)


def _universal_solution_transformation(
    values: UniversalRightTriangleValues,
    *,
    side_latex: dict[str, str],
    third_side: str,
) -> dict[str, Any]:
    """Build two or three concise rows from normalized right-triangle roles."""

    function = rf"\{values.trig_name} {values.trig_angle}"
    numerator = values.numerator_side
    denominator = values.denominator_side
    known = values.known_side
    requested = values.requested_side
    trig = values.trig_latex
    definition = rf"{function}=\frac{{{numerator}}}{{{denominator}}}"
    rows: list[str] = []
    if {known, requested} == {numerator, denominator}:
        if known == numerator:
            rows.append(
                definition + rf"\iff {denominator}=\frac{{{numerator}}}{{{function}}}="
                rf"\frac{{{values.known_latex}}}{{{trig}}}={side_latex[denominator]}"
            )
        else:
            rows.append(
                definition + rf"\iff {numerator}={denominator}\cdot{function}="
                rf"{values.known_latex}\cdot {trig}={side_latex[numerator]}"
            )
    elif known in {numerator, denominator}:
        if known == numerator:
            calculated = denominator
            rows.append(
                definition + rf"\iff {denominator}=\frac{{{numerator}}}{{{function}}}="
                rf"\frac{{{values.known_latex}}}{{{trig}}}={side_latex[denominator]}"
            )
        else:
            calculated = numerator
            rows.append(
                definition + rf"\iff {numerator}={denominator}\cdot{function}="
                rf"{values.known_latex}\cdot {trig}={side_latex[numerator]}"
            )
        if requested == values.hypotenuse:
            legs = sorted({"AB", "AC", "BC"} - {values.hypotenuse})
            rows.append(
                rf"{requested}=\sqrt{{{legs[0]}^{{2}}+{legs[1]}^{{2}}}}="
                rf"\sqrt{{{side_latex[legs[0]]}^{{2}}+{side_latex[legs[1]]}^{{2}}}}="
                rf"{side_latex[requested]}"
            )
        else:
            other_leg = ({"AB", "AC", "BC"} - {values.hypotenuse, requested}).pop()
            rows.append(
                rf"{requested}=\sqrt{{{values.hypotenuse}^{{2}}-{other_leg}^{{2}}}}="
                rf"\sqrt{{{side_latex[values.hypotenuse]}^{{2}}-{side_latex[other_leg]}^{{2}}}}="
                rf"{side_latex[requested]}"
            )
        if calculated == requested:
            raise RightTrianglePlanError(
                "universal solution selected a redundant third row"
            )
    else:
        if known != third_side:
            raise RightTrianglePlanError(
                "known side is outside normalized triangle roles"
            )
        if values.trig_name in {"sin", "cos"}:
            complement_name = "cos" if values.trig_name == "sin" else "sin"
            complement = rf"\{complement_name} {values.trig_angle}"
            complement_latex = _positive_root_latex(Fraction(1) - _trig_square(trig))
            rows.extend(
                [
                    (
                        rf"{complement}=\sqrt{{1-{function}^2}}="
                        rf"\sqrt{{1-({trig})^2}}={complement_latex}"
                    ),
                    (
                        rf"{complement}=\frac{{{known}}}{{{denominator}}}"
                        rf"\iff {denominator}=\frac{{{known}}}{{{complement}}}="
                        rf"\frac{{{values.known_latex}}}{{{complement_latex}}}="
                        rf"{side_latex[denominator]}"
                    ),
                ]
            )
            if requested == numerator:
                rows.append(
                    definition + rf"\iff {numerator}={denominator}\cdot{function}="
                    rf"{side_latex[denominator]}\cdot {trig}={side_latex[numerator]}"
                )
            elif requested != denominator:
                raise RightTrianglePlanError(
                    "requested side is outside normalized triangle roles"
                )
            return _universal_solution_rows_transformation(rows)
        rows.append(definition)
        sign = "-" if denominator == values.hypotenuse else "+"
        rows.append(
            rf"{denominator}=\frac{{{known}}}{{\sqrt{{1{sign}({function})^2}}}}="
            rf"\frac{{{values.known_latex}}}{{\sqrt{{1{sign}({trig})^2}}}}="
            rf"{side_latex[denominator]}"
        )
        if requested == numerator:
            rows.append(
                rf"{numerator}={denominator}\cdot{function}="
                rf"{side_latex[denominator]}\cdot {trig}={side_latex[numerator]}"
            )
        elif requested != denominator:
            raise RightTrianglePlanError(
                "requested side is outside normalized triangle roles"
            )
    return _universal_solution_rows_transformation(rows)


def _universal_solution_rows_transformation(rows: list[str]) -> dict[str, Any]:
    """Wrap verified universal formula rows in one solution transformation."""

    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-universal" '
        'data-solution-title="Решение">'
        "<p>По определению тригонометрической функции:</p>"
        + "".join(
            '<center><p><span data-inline-latex="' + row + '"></span></p></center>'
            for row in rows
        )
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _universal_trig_request_solution_transformation(
    values: UniversalTrigRequestValues,
    *,
    side_latex: dict[str, str],
    missing_side: str,
    answer: str,
) -> dict[str, Any]:
    """Build two or three concise rows for a requested trig value."""

    rows: list[str] = []
    if missing_side == values.hypotenuse and missing_side in {
        values.numerator_side,
        values.denominator_side,
    }:
        legs = sorted({"AB", "AC", "BC"} - {values.hypotenuse})
        rows.append(
            rf"{values.hypotenuse}=\sqrt{{{legs[0]}^{{2}}+{legs[1]}^{{2}}}}="
            rf"\sqrt{{({side_latex[legs[0]]})^{{2}}+({side_latex[legs[1]]})^{{2}}}}="
            rf"{side_latex[values.hypotenuse]}"
        )
    elif missing_side in {values.numerator_side, values.denominator_side}:
        other_leg = ({"AB", "AC", "BC"} - {values.hypotenuse, missing_side}).pop()
        rows.append(
            rf"{missing_side}=\sqrt{{{values.hypotenuse}^{{2}}-{other_leg}^{{2}}}}="
            rf"\sqrt{{({side_latex[values.hypotenuse]})^{{2}}-({side_latex[other_leg]})^{{2}}}}="
            rf"{side_latex[missing_side]}"
        )
    function = rf"\{values.trig_name} {values.trig_angle}"
    rows.append(
        rf"{function}=\frac{{{values.numerator_side}}}{{{values.denominator_side}}}="
        rf"\frac{{{side_latex[values.numerator_side]}}}"
        rf"{{{side_latex[values.denominator_side]}}}=" + answer.replace(",", "{,}")
    )
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-universal" '
        'data-solution-title="Решение">'
        "<p>Используем соотношения сторон прямоугольного треугольника:</p>"
        + "".join(
            '<center><p><span data-inline-latex="' + row + '"></span></p></center>'
            for row in rows
        )
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }
