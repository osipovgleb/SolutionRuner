"""Regression coverage for source group 282849."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_282849_planner import RULE, build_repair_plan
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


def _context(formula: str, answer: str = "") -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "section_id": "condition:1", "transformation_target_id": "section:condition:1", "asset_keys": [], "html": f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>.</p>'},
        {"key": "answer", "section_id": "answer:1", "transformation_target_id": "section:answer:1", "html": f"<p>{answer}</p>"},
    ]}}


def _plan(context: dict):
    return build_repair_plan(context, parent_condition_asset_id=None)


def _solution(plan) -> str:
    return next(change["value"]["html"] for change in plan.transformations if change["transformation_target_id"] == "section:solution")


def test_profile_is_registered_with_an_assetless_content_rule() -> None:
    profile = get_group_profile("282849")
    assert profile.source_group_id == "e6bc1d8d-7f3e-475e-9963-1c9f9ae848ee"
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id is None


def test_parent_and_real_child_recompute_different_values() -> None:
    parent = _plan(_context(r"(x-1)^{3}=8", "3"))
    child = _plan(_context(r"(x-3)^{3}=343", "7"))
    assert parent.answer == "3"
    assert child.answer == "10"
    assert r"x-3=7" in _solution(child)
    assert r"x=10" in _solution(child)


def test_wrong_answer_is_rewritten_to_computed_answer() -> None:
    plan = _plan(_context(r"(x-3)^{3}=343", "7"))
    answer = next(change["value"]["html"] for change in plan.transformations if change["transformation_target_id"] == "section:answer:1")
    assert answer == '<p><span data-effect="spaced">10</span></p>'


def test_second_audited_plus_shift_form_is_computed() -> None:
    plan = _plan(_context(r"(x+1)^{3}=1", "0"))
    assert plan.answer == "0"
    assert r"x+1=1" in _solution(plan)
    assert r"x=0" in _solution(plan)


def test_failed_manifest_fifth_power_form_is_already_complete() -> None:
    plan = _plan(_context(r"(x+8)^{5}=243", "-5"))
    assert plan.answer == "-5"
    assert "пятой сте­пе­ни" in _solution(plan)


def test_failed_manifest_negative_odd_power_is_computed() -> None:
    plan = _plan(_context(r"(x+4)^{3}=-125", "-9"))
    assert plan.answer == "-9"
    assert r"x+4=-5" in _solution(plan)


@pytest.mark.parametrize(
    ("formula", "expected"),
    [(r"(x-1)^{7}=1", "2"), (r"x^{11}=-2048", "-2")],
)
def test_any_positive_odd_degree_is_computed(formula: str, expected: str) -> None:
    assert _plan(_context(formula)).answer == expected


@pytest.mark.parametrize("formula", [r"x^{2}=343", r"(x-3)^{4}=81", r"(x-3)^{3}=10"])
def test_unresearched_forms_fail_closed(formula: str) -> None:
    with pytest.raises(RightTrianglePlanError):
        _plan(_context(formula))


def test_unexpected_asset_fails_closed() -> None:
    context = deepcopy(_context(r"(x-3)^{3}=343"))
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})
    with pytest.raises(RightTrianglePlanError):
        _plan(context)
