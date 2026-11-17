"""Shared right-triangle repair plan and content validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .altitude_solver import AltitudeSolveError
from .planner_conditions import _plain_html


@dataclass(frozen=True)
class RepairPlan:
    """Describe the minimal durable transformations for one source problem."""

    answer: str
    transformations: tuple[dict[str, Any], ...]


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return the unique normalized section with the canonical key."""

    matches = [
        section
        for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(matches) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return matches[0] if matches else None


def _parent_triangle_plan(
    context,
    parent_asset_id,
    parent_solution_html,
    *,
    required_trig_name=None,
    required_requested=None,
):
    from .basic_parent import prepare

    try:
        return prepare(
            context,
            parent_asset_id=parent_asset_id,
            parent_solution_html=parent_solution_html,
            required_trig_name=required_trig_name,
            required_requested=required_requested,
        )
    except AltitudeSolveError as exc:
        raise RightTrianglePlanError(str(exc)) from exc


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    """Return whether one answer section equals the computed numeric value."""

    if section is None:
        return False
    current = _plain_html(str(section.get("html") or "")).replace(" ", "")
    if current == expected:
        return True
    try:
        return Fraction(current.replace(",", ".")) == Fraction(
            expected.replace(",", ".")
        )
    except (ValueError, ZeroDivisionError):
        return False
