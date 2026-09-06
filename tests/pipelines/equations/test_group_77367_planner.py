"""Coverage for the second rational-equation group."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_77367_planner import RULE, build_repair_plan
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


def _context(formula: str, kind: str, answer: str = "") -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "section_id": "condition:1", "transformation_target_id": "section:condition:1", "asset_keys": [], "html": f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>. Если урав­не­ние имеет более од­но­го корня, в от­ве­те за­пи­ши­те {kind} из кор­ней.</p>'},
        {"key": "answer", "section_id": "answer:1", "transformation_target_id": "section:answer:1", "html": f"<p>{answer}</p>"},
    ]}}


def _plan(context: dict):
    return build_repair_plan(context, parent_condition_asset_id=None)


def test_profile_is_registered() -> None:
    profile = get_group_profile("77367")
    assert profile.content_rule_key == RULE
    assert profile.source_group_id == "7d24a3f9-43d9-4ee7-8548-ad79581ecf47"


def test_parent_and_audited_child_recompute_values() -> None:
    assert _plan(_context(r"\frac{13x}{2x^{2}-7}=1", "меньший", "-0,5")).answer == "-0,5"
    child = _plan(_context(r"\frac{7x}{3x^{2}-10}=1", "меньший"))
    assert child.answer == "-1"
    solution = next(x["value"]["html"] for x in child.transformations if x["transformation_target_id"] == "section:solution")
    assert r"D=b^2-4ac=(-7)^{2}-4\cdot3\cdot(-10)=169" in solution
    assert r"\frac{10}{3}" in solution


def test_plus_sign_and_implicit_quadratic_coefficient_are_supported() -> None:
    plan = _plan(_context(r"\frac{25x}{x^{2}+24}=1", "больший", "0"))
    assert plan.answer == "24"
    solution = next(x["value"]["html"] for x in plan.transformations if x["transformation_target_id"] == "section:solution")
    assert r"x^{2}-25x+24=0" in solution
    assert r"D=b^2-4ac=(-25)^{2}-4\cdot1\cdot24=529" in solution


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        (r"\frac{23x}{2x^{2}+15}=2", "2"),
        (r"\frac{19x}{x^{2}-23}=2", "-2"),
    ],
)
def test_positive_integer_right_hand_side_is_a_parameter(formula: str, expected: str) -> None:
    assert _plan(_context(formula, "меньший")).answer == expected


def test_requested_smaller_positive_root_keeps_the_selector_wording() -> None:
    plan = _plan(_context(r"\frac{5x}{x^{2}+6}=1", "меньший"))
    assert plan.answer == "2"
    solution = next(x["value"]["html"] for x in plan.transformations if x["transformation_target_id"] == "section:solution")
    assert "мень\u00adший" in solution


@pytest.mark.parametrize("formula", [r"\frac{7x}{3x^{2}-10}=3", r"\frac{7x}{3x^{2}-9}=1", r"\frac{7x}{3x^{2}-10}=1x", r"\frac{7x}{3x^{2}+10}=1"])
def test_unsupported_forms_fail_closed(formula: str) -> None:
    with pytest.raises(RightTrianglePlanError):
        _plan(_context(formula, "меньший"))


def test_assets_fail_closed() -> None:
    context = deepcopy(_context(r"\frac{7x}{3x^{2}-10}=1", "меньший"))
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})
    with pytest.raises(RightTrianglePlanError):
        _plan(context)
