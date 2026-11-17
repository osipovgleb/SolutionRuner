"""Build right-triangle repairs involving an altitude."""

from __future__ import annotations

from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .altitude_solver import AltitudeSolveError, solve_altitude_condition
from .altitude_solver import answer_matches as altitude_answer_matches
from .planner_common import RepairPlan, _section
from .planner_conditions import _plain_html
from .planner_transformations import _answer_transformation, _asset_transformation

_ALTITUDE_CONTENT_VERSION = "10"


def build_altitude_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    parent_solution_html: str | None = None,
) -> RepairPlan:
    """Return a fail-closed repair for right triangles split by altitude CH."""

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
    if parent_solution_html is not None:
        from .altitude_parent import prepare

        try:
            return prepare(
                context,
                parent_asset_id=parent_asset_id,
                parent_solution_html=parent_solution_html,
            )
        except AltitudeSolveError as exc:
            raise RightTrianglePlanError(str(exc)) from exc
    try:
        solved = solve_altitude_condition(str(condition.get("html") or ""))
    except AltitudeSolveError as exc:
        raise RightTrianglePlanError(str(exc)) from exc

    answer_needs_repair = answer_section is None
    if answer_section is not None:
        try:
            answer_needs_repair = not altitude_answer_matches(
                str(answer_section.get("html") or ""),
                solved.exact_value,
            )
        except AltitudeSolveError:
            answer_needs_repair = True

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
    solution_has_content = bool(_plain_html(solution_html)) or (
        'data-inline-latex="' in solution_html
    )
    stale_runner_solution = (
        'data-content-rule="right-triangle-altitude-universal"' in solution_html
        and f'data-content-version="{_ALTITUDE_CONTENT_VERSION}"' not in solution_html
    )
    if solution is None or not solution_has_content or stale_runner_solution:
        rendered_steps: list[str] = []
        for row in solved.rows:
            intro = _altitude_step_intro(row)
            if intro:
                rendered_steps.append(f"<p>{intro}</p>")
            rendered_steps.append(
                '<center><p><span data-inline-latex="' + row + '"></span></p></center>'
            )
        html = (
            '<section data-content-kind="solution" '
            'data-content-rule="right-triangle-altitude-universal" '
            f'data-content-version="{_ALTITUDE_CONTENT_VERSION}" '
            'data-solution-title="Решение">' + "".join(rendered_steps) + "</section>"
        )
        transformations.append(
            {
                "transformation_target_id": "section:solution",
                "operation": "add" if solution is None else "rewrite",
                "value": {"title": "Решение", "html": html, "asset_keys": []},
            }
        )
    if answer_needs_repair:
        transformations.append(_answer_transformation(solved.answer))
    return RepairPlan(answer=solved.answer, transformations=tuple(transformations))


def _altitude_step_intro(row: str) -> str:
    """Return one concise geometric transition before a formula block."""

    pythagorean_triangles = {
        "AB^2=AC^2+BC^2": "ABC",
        "AC^2=AH^2+CH^2": "ACH",
        "BC^2=BH^2+CH^2": "BCH",
    }
    triangle = pythagorean_triangles.get(row)
    if triangle is not None:
        return (
            "По теореме Пифагора для "
            f'<span data-inline-latex="\\triangle {triangle}"></span>:'
        )

    function_name = next(
        (
            label
            for prefix, label in (
                (r"\sin A=", "синуса"),
                (r"\cos A=", "косинуса"),
                (r"\tg A=", "тангенса"),
            )
            if row.startswith(prefix)
        ),
        None,
    )
    if function_name is None:
        return ""
    ratio_triangles = (
        ("ABC", (r"\frac{BC}{AB}", r"\frac{AC}{AB}", r"\frac{BC}{AC}")),
        ("ACH", (r"\frac{CH}{AC}", r"\frac{AH}{AC}", r"\frac{CH}{AH}")),
        ("BCH", (r"\frac{BH}{BC}", r"\frac{CH}{BC}", r"\frac{BH}{CH}")),
    )
    triangle = next(
        (
            name
            for name, ratios in ratio_triangles
            if any(ratio in row for ratio in ratios)
        ),
        None,
    )
    if triangle == "BCH":
        return (
            'Так как <span data-inline-latex="\\angle BCH=\\angle A"></span>, '
            f"по определению {function_name} в "
            '<span data-inline-latex="\\triangle BCH"></span>:'
        )
    return (
        f"По определению {function_name} в "
        f'<span data-inline-latex="\\triangle {triangle}"></span>:'
        if triangle is not None
        else ""
    )
