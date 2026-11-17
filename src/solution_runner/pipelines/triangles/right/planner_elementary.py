"""Plan elementary right-triangle content repairs."""

from __future__ import annotations

from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .altitude_solver import AltitudeSolveError
from .planner_altitude_rows import (
    _altitude_length_rows,
    _hypotenuse_projection_ah_rows,
    _hypotenuse_projection_bh_rows,
)
from .planner_angle_rows import (
    _altitude_bisector_angle_rows,
    _altitude_bisector_inverse_rows,
    _altitude_line_angle_rows,
    _altitude_median_inverse_rows,
    _bisector_intersection_angle_rows,
    _bisector_median_angle_rows,
    _bisector_median_inverse_rows,
    _median_angle_rows,
)
from .planner_area_rows import (
    _acute_angle_difference_rows,
    _acute_angle_ratio_rows,
    _area_leg_difference_rows,
    _leg_hypotenuse_area_rows,
)
from .planner_common import RepairPlan, _answer_matches, _section
from .planner_conditions import _plain_html
from .planner_elementary_intro import _elementary_intro
from .planner_transformations import (
    _answer_transformation,
    _asset_transformation,
    _elementary_solution_transformation,
)

_ELEMENTARY_RULES = {
    "right-triangle-leg-hypotenuse-area": _leg_hypotenuse_area_rows,
    "right-triangle-area-leg-difference": _area_leg_difference_rows,
    "right-triangle-acute-angle-difference": _acute_angle_difference_rows,
    "right-triangle-acute-angle-ratio": _acute_angle_ratio_rows,
    "right-triangle-median-angle": _median_angle_rows,
    "right-triangle-bisector-intersection-angle": _bisector_intersection_angle_rows,
    "right-triangle-altitude-bisector-angle": _altitude_bisector_angle_rows,
    "right-triangle-altitude-bisector-inverse": _altitude_bisector_inverse_rows,
    "right-triangle-altitude-line-angle": _altitude_line_angle_rows,
    "right-triangle-altitude-median-inverse": _altitude_median_inverse_rows,
    "right-triangle-bisector-median-angle": _bisector_median_angle_rows,
    "right-triangle-bisector-median-inverse": _bisector_median_inverse_rows,
    "right-triangle-altitude-length": _altitude_length_rows,
    "right-triangle-hypotenuse-projection-ah": _hypotenuse_projection_ah_rows,
    "right-triangle-hypotenuse-projection-bh": _hypotenuse_projection_bh_rows,
}


def build_elementary_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    content_rule_key: str,
    parent_solution_html: str | None = None,
) -> RepairPlan:
    """Return a strict image, solution, and answer repair for one elementary rule."""

    if parent_solution_html is not None:
        from .elementary_parent import prepare

        try:
            return prepare(
                context,
                parent_asset_id=parent_asset_id,
                parent_solution_html=parent_solution_html,
                content_rule_key=content_rule_key,
            )
        except AltitudeSolveError as exc:
            raise RightTrianglePlanError(str(exc)) from exc
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    try:
        solver = _ELEMENTARY_RULES[content_rule_key]
    except KeyError as exc:
        raise RightTrianglePlanError("unsupported elementary content rule") from exc
    condition_html = str(condition.get("html") or "")
    answer, rows = solver(condition_html)
    intro = _elementary_intro(content_rule_key, condition_html)
    desired_solution = _elementary_solution_transformation(
        content_rule_key,
        intro,
        rows,
    )
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
    if solution is None or not _plain_html(solution_html):
        transformations.append(desired_solution)
    elif (
        f'data-content-rule="{content_rule_key}"' in solution_html
        and solution_html != desired_solution["value"]["html"]
    ):
        transformations.append(
            _elementary_solution_transformation(
                content_rule_key,
                intro,
                rows,
                operation="rewrite",
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))
