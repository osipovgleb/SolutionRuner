"""Regression coverage for source group 282850."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.equations.group_282850_planner import build_repair_plan


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>'},
        {"key": "answer", "section_id": "answer:1", "html": "<p></p>"},
    ]}}


@pytest.mark.parametrize(
    ("formula", "answer"),
    [(r"(x-1)^{7}=-1", "0"), (r"(x+6)^{7}=-128", "-8")],
)
def test_audited_seventh_power_tasks_are_computed(formula: str, answer: str) -> None:
    plan = build_repair_plan(_context(formula), parent_condition_asset_id=None)
    assert plan.answer == answer
