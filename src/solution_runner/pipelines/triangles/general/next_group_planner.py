"""Parent-faithful handlers for the audited general-triangle groups after 27767."""

from __future__ import annotations

from typing import Any

from ..isosceles.planner import (
    _asset_transformation,
    _normalized_content,
    _section,
    _section_transformation,
    _solution_asset_transformation,
)
from ..right.planner import RepairPlan, RightTrianglePlanError
from .next_group_proofs import (
    _BUILDERS,
    _answer_matches,
    _answer_text,
    _condition_stream,
    _has_condition_asset,
)

RULES = frozenset(
    {
        "general-triangle-27768-bisector-equal-segments-angle",
        "general-triangle-27769-extension-isosceles-angle",
        "general-triangle-27776-bisector-congruent-angle",
        "general-triangle-27777-exterior-bisector-isosceles-angle",
        "general-triangle-27778-incenter-bisectors-angle",
        "general-triangle-27779-orthocenter-altitudes-angle",
        "general-triangle-317337-midline-small-area-to-total",
        "general-triangle-319058-midline-trapezoid-area",
        "general-triangle-500142-altitudes-obtuse-angle",
        "general-triangle-510796-extended-altitudes-angle",
    }
)


def build_repair_plan(
    context: dict[str, Any],
    *,
    rule: str,
    parent_solution_html: str,
    parent_condition_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
) -> RepairPlan:
    """Build one strict repair with the handler registered for its source group."""

    builder = _BUILDERS.get(rule)
    if builder is None:
        raise RightTrianglePlanError("unsupported next general-triangle rule")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    answer, solution_html = builder(
        _condition_stream(str(condition.get("html") or "")), parent_solution_html
    )
    answer_text = _answer_text(answer)
    changes: list[dict[str, Any]] = []

    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer_text}</span></p>',
            )
        )

    solution = _section(content, "solution")
    if rule == "general-triangle-319058-midline-trapezoid-area":
        solution_assets = ()
    elif rule == "general-triangle-317337-midline-small-area-to-total":
        solution_assets = tuple(
            item
            for item in parent_solution_assets
            if item.get("asset_key") == "image_2"
        )
    else:
        solution_assets = parent_solution_assets
    solution_asset_keys = tuple(
        str(item.get("asset_key") or "") for item in solution_assets
    )

    if rule == "general-triangle-317337-midline-small-area-to-total":
        condition_images = [
            item
            for item in parent_solution_assets
            if item.get("asset_key") == "image_1"
        ]
        if len(condition_images) != 1:
            raise RightTrianglePlanError("group 317337 parent must provide image_1")
        condition_asset_id = str(condition_images[0].get("source_asset_id") or "")
        if not _has_condition_asset(condition, condition_asset_id):
            changes.append(_asset_transformation(condition_asset_id))

    current_solution = str(solution.get("html") or "") if solution else ""
    current_keys = tuple(str(key) for key in (solution or {}).get("asset_keys", []))
    if current_solution != solution_html or current_keys != solution_asset_keys:
        changes.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
                asset_keys=solution_asset_keys,
            )
        )

    if solution_assets:
        expected = (
            ("image_2",)
            if rule == "general-triangle-317337-midline-small-area-to-total"
            else tuple(f"image_{index}" for index in range(1, len(solution_assets) + 1))
        )
        if solution_asset_keys != expected:
            raise RightTrianglePlanError(
                "parent solution assets are not consecutive image keys"
            )
        current_assets = {
            str(item.get("asset_key") or ""): str(item.get("asset_id") or "")
            for item in content.get("assets", [])
            if isinstance(item, dict)
        }
        for item in solution_assets:
            key = str(item.get("asset_key") or "")
            if current_assets.get(key) != str(item.get("source_asset_id") or ""):
                changes.append(
                    _solution_asset_transformation(item, expected_asset_key=key)
                )
    elif rule != "general-triangle-317337-midline-small-area-to-total":
        condition_asset_id = parent_condition_asset_id
        if rule == "general-triangle-319058-midline-trapezoid-area":
            if len(parent_solution_assets) != 1:
                raise RightTrianglePlanError(
                    "group 319058 parent must provide one image"
                )
            condition_asset_id = str(
                parent_solution_assets[0].get("source_asset_id") or ""
            )
        if not _has_condition_asset(condition, condition_asset_id):
            changes.append(_asset_transformation(condition_asset_id))

    return RepairPlan(answer=answer_text, transformations=tuple(changes))


def build_group_27769_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-27769-extension-isosceles-angle", **kwargs
    )


def build_group_27768_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-27768-bisector-equal-segments-angle", **kwargs
    )


def build_group_27776_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-27776-bisector-congruent-angle", **kwargs
    )


def build_group_27777_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context,
        rule="general-triangle-27777-exterior-bisector-isosceles-angle",
        **kwargs,
    )


def build_group_27778_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-27778-incenter-bisectors-angle", **kwargs
    )


def build_group_27779_repair_plan(context: dict[str, Any], **kwargs: Any) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-27779-orthocenter-altitudes-angle", **kwargs
    )


def build_group_317337_repair_plan(
    context: dict[str, Any], **kwargs: Any
) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-317337-midline-small-area-to-total", **kwargs
    )


def build_group_319058_repair_plan(
    context: dict[str, Any], **kwargs: Any
) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-319058-midline-trapezoid-area", **kwargs
    )


def build_group_500142_repair_plan(
    context: dict[str, Any], **kwargs: Any
) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-500142-altitudes-obtuse-angle", **kwargs
    )


def build_group_510796_repair_plan(
    context: dict[str, Any], **kwargs: Any
) -> RepairPlan:
    return build_repair_plan(
        context, rule="general-triangle-510796-extended-altitudes-angle", **kwargs
    )
