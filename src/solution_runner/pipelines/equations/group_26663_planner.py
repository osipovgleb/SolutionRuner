"""Strict repair planner for elementary-equation group 26663."""

from __future__ import annotations

from typing import Any

from .group_26662_planner import build_repair_plan as _build_repair_plan
from ..triangles.right.planner import RepairPlan


RULE = "elementary-equations-26663-negative-fractional-linear-equation"
PARENT_PROBLEM_ID = "063581d9-05ab-46e9-bf59-0c7a29a1bf3b"


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    """Compute the audited negative-root version of the fractional equation."""

    return _build_repair_plan(
        context,
        parent_condition_asset_id=parent_condition_asset_id,
        parent_solution_html=parent_solution_html,
        current_asset_content_type=current_asset_content_type,
        allow_negative_answer=True,
    )
