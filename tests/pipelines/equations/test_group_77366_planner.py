"""Coverage for the first rational-equation group."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_77366_planner import RULE, build_repair_plan
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
    profile = get_group_profile("77366")
    assert profile.content_rule_key == RULE
    assert profile.source_group_id == "3df0b902-e956-44e5-af04-795dadaf7d56"


def test_parent_and_real_child_recompute_values() -> None:
    assert _plan(_context(r"\frac{9}{x^{2}-16}=1", "больший", "5")).answer == "5"
    child = _plan(_context(r"\frac{8}{x^{2}-8}=1", "больший", "4"))
    assert child.answer == "4"
    solution = next(x["value"]["html"] for x in child.transformations if x["transformation_target_id"] == "section:solution")
    assert r"x^{2}-8=8\iff x^{2}=16" in solution


def test_smaller_root_and_wrong_answer_are_repaired() -> None:
    plan = _plan(_context(r"\frac{12}{x^{2}-4}=1", "меньший", "4"))
    assert plan.answer == "-4"
    answer = next(x["value"]["html"] for x in plan.transformations if x["transformation_target_id"] == "section:answer:1")
    assert ">-4<" in answer


def test_second_audited_plus_denominator_form_repairs_wrong_answer() -> None:
    plan = _plan(_context(r"\frac{15}{x^{2}+14}=1", "больший", "0"))
    assert plan.answer == "1"
    solution = next(x["value"]["html"] for x in plan.transformations if x["transformation_target_id"] == "section:solution")
    assert r"x^{2}+14=15\iff x^{2}=1" in solution


def test_alternative_retrieve_wording_without_final_period_is_accepted() -> None:
    context = _context(r"\frac{14}{x^{2}-2}=1", "меньший", "-4")
    context["normalized_content"]["sections"][0]["html"] = context["normalized_content"]["sections"][0]["html"].replace("Най­ди­те", "Ре­ши­те").replace(".</p>", "</p>")
    assert _plan(context).answer == "-4"


@pytest.mark.parametrize("formula", [r"\frac{8}{x^{2}-8}=2", r"\frac{8}{x^{2}-7}=1", r"\frac{8}{x^{2}+8}=1"])
def test_unsupported_forms_fail_closed(formula: str) -> None:
    with pytest.raises(RightTrianglePlanError):
        _plan(_context(formula, "больший"))


def test_assets_fail_closed() -> None:
    context = deepcopy(_context(r"\frac{8}{x^{2}-8}=1", "больший"))
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})
    with pytest.raises(RightTrianglePlanError):
        _plan(context)
