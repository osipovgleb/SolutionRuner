"""Regression tests for the group-26667 quadratic-root runner."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_26667_planner import (
    build_repair_plan,
)
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)


def _context(formula: str, *, kind: str = "меньший", answer: str = "") -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "transformation_target_id": "section:condition:1",
                    "asset_keys": [],
                    "html": (
                        '<p>Най­ди­те ко­рень урав­не­ния: '
                        f'<span data-inline-latex="{formula}"></span>. '
                        "Если урав­не­ние имеет более од­но­го корня, ука­жи­те "
                        f"{kind} из них.</p>"
                    ),
                },
                {"key": "answer", "section_id": "answer:1", "html": f"<p>{answer}</p>"},
            ],
        }
    }


def _solution(plan) -> str:
    return next(item["value"]["html"] for item in plan.transformations if item["transformation_target_id"] == "section:solution")


def test_parent_layout_has_discriminant_before_one_root_collection() -> None:
    plan = build_repair_plan(_context(r"x^{2}-17x+72=0"), parent_condition_asset_id=None)

    assert plan.answer == "8"
    html = _solution(plan)
    assert "фор­му­лой дис­кри­ми­нан­та" in html
    assert r"D=b^2-4ac=(-17)^{2}-4\cdot1\cdot72=1" in html
    assert r"\sqrt{289-288}" in html
    assert html.count(r"\left[\begin{aligned}") == 2


@pytest.mark.parametrize(
    ("formula", "kind", "expected"),
    [
        (r"x^{2}-x-72=0", "меньший", "-8"),
        (r"x^{2}-36=0", "меньший", "-6"),
        (r"x^{2}+4x=0", "меньший", "-4"),
        (r"2x^{2}-33x+136=0", "больший", "8,5"),
    ],
)
def test_accepted_canonical_forms_compute_requested_root(formula: str, kind: str, expected: str) -> None:
    assert build_repair_plan(_context(formula, kind=kind), parent_condition_asset_id="").answer == expected


def test_non_square_discriminant_fails_closed() -> None:
    with pytest.raises(RightTrianglePlanError, match="discriminant"):
        build_repair_plan(_context(r"x^{2}+x-1=0"), parent_condition_asset_id=None)


def test_unexpected_asset_fails_closed() -> None:
    context = deepcopy(_context(r"x^{2}-36=0"))
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context, parent_condition_asset_id=None)
