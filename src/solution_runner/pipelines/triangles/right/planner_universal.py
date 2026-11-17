"""Build universal right-triangle repairs for side and trigonometric requests."""

from __future__ import annotations

import math
from fractions import Fraction
from html import unescape
from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_common import RepairPlan, _answer_matches, _parent_triangle_plan, _section
from .planner_conditions import _plain_html
from .planner_notation import (
    _answer_text,
    _numeric_square_latex,
    _positive_root_number_latex,
    _trig_square,
)
from .planner_transformations import _answer_transformation, _asset_transformation
from .planner_universal_parse import (
    UniversalTrigRequestValues,
    _universal_trig_request_values,
    _universal_values,
)
from .planner_universal_render import (
    _universal_solution_transformation,
    _universal_trig_request_solution_transformation,
)


def build_universal_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    parent_solution_html: str | None = None,
) -> RepairPlan:
    """Return a role-normalized repair for any supported right triangle."""

    if parent_solution_html is not None:
        return _parent_triangle_plan(
            context,
            parent_asset_id,
            parent_solution_html,
        )
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    trig_request = _universal_trig_request_values(condition_html)
    if trig_request is not None:
        return _build_universal_trig_request_plan(
            content,
            answer_section=answer_section,
            values=trig_request,
            parent_asset_id=parent_asset_id,
        )
    values = _universal_values(condition_html)
    trig_squared = _trig_square(values.trig_latex)
    if values.trig_name in {"sin", "cos"}:
        if not 0 < trig_squared < 1:
            raise RightTrianglePlanError(
                "sin or cos of an acute angle must be between zero and one"
            )
    elif trig_squared <= 0:
        raise RightTrianglePlanError("tg or ctg of an acute angle must be positive")

    sides = {"AB", "AC", "BC"}
    third_side = (sides - {values.numerator_side, values.denominator_side}).pop()
    if values.denominator_side == values.hypotenuse:
        coefficients = {
            values.hypotenuse: Fraction(1),
            values.numerator_side: trig_squared,
            third_side: 1 - trig_squared,
        }
    else:
        coefficients = {
            values.denominator_side: Fraction(1),
            values.numerator_side: trig_squared,
            values.hypotenuse: 1 + trig_squared,
        }
    known_squared = _numeric_square_latex(values.known_latex)
    if known_squared <= 0:
        raise RightTrianglePlanError("known side must be positive")
    scale_squared = known_squared / coefficients[values.known_side]
    side_squares = {
        side: scale_squared * coefficient for side, coefficient in coefficients.items()
    }
    side_latex = {
        side: _positive_root_number_latex(square)
        for side, square in side_squares.items()
    }
    answer = _answer_text(math.sqrt(float(side_squares[values.requested_side])))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if (
        not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_asset_id
    ):
        transformations.append(_asset_transformation(parent_asset_id))

    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    runner_solution_needs_refresh = (
        'data-content-rule="right-triangle-universal"' in solution_html
        and ("</span>.</p>" in solution_html or r"\iff" not in unescape(solution_html))
    )
    if (
        solution is None
        or not _plain_html(solution_html)
        or runner_solution_needs_refresh
    ):
        transformations.append(
            _universal_solution_transformation(
                values,
                side_latex=side_latex,
                third_side=third_side,
            )
        )
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def _build_universal_trig_request_plan(
    content: dict[str, Any],
    *,
    answer_section: dict[str, Any] | None,
    values: UniversalTrigRequestValues,
    parent_asset_id: str,
) -> RepairPlan:
    """Build a repair when two sides are given and a trig value is requested."""

    side_squares = {
        side: _numeric_square_latex(latex) for side, latex in values.known_sides
    }
    if any(square <= 0 for square in side_squares.values()):
        raise RightTrianglePlanError("known sides must be positive")
    all_sides = {"AB", "AC", "BC"}
    missing_side = (all_sides - set(side_squares)).pop()
    if missing_side == values.hypotenuse:
        side_squares[missing_side] = sum(side_squares.values(), Fraction())
    else:
        if values.hypotenuse not in side_squares:
            raise RightTrianglePlanError(
                "two legs or the hypotenuse and one leg are required"
            )
        other_leg = (all_sides - {values.hypotenuse, missing_side}).pop()
        missing_square = side_squares[values.hypotenuse] - side_squares[other_leg]
        if missing_square <= 0:
            raise RightTrianglePlanError("hypotenuse must be longer than a known leg")
        side_squares[missing_side] = missing_square

    side_latex = dict(values.known_sides)
    side_latex[missing_side] = _positive_root_number_latex(side_squares[missing_side])
    trig_square = (
        side_squares[values.numerator_side] / side_squares[values.denominator_side]
    )
    answer = _answer_text(math.sqrt(float(trig_square)))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if (
        not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_asset_id
    ):
        transformations.append(_asset_transformation(parent_asset_id))

    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    runner_solution_needs_refresh = (
        'data-content-rule="right-triangle-universal"' in solution_html
        and "</span>.</p>" in solution_html
    )
    if (
        solution is None
        or not _plain_html(solution_html)
        or runner_solution_needs_refresh
    ):
        transformations.append(
            _universal_trig_request_solution_transformation(
                values,
                side_latex=side_latex,
                missing_side=missing_side,
                answer=answer,
            )
        )
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))
