"""Regression coverage for arbitrary odd roots of affine expressions."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.equations.group_27466 import (
    RULE,
    UnsupportedCondition,
    build_context_repair_plan,
    build_repair_plan,
)


def _context(formula: str, answer: str = "") -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "transformation_target_id": "section:condition:1", "asset_keys": [], "html": f'<p>Найдите корень уравнения <span data-inline-latex="{formula}"></span>.</p>'},
        {"key": "answer", "transformation_target_id": "section:answer:1", "asset_keys": [], "html": f"<p>{answer}</p>"},
    ]}}


def test_group_is_registered_with_its_own_odd_root_rule() -> None:
    profile = get_group_profile("27466")
    assert profile.source_group_id == "d91565fb-3672-4b3a-89c5-ffdf964a7309"
    assert profile.content_rule_key == RULE


@pytest.mark.parametrize(
    ("formula", "answer"),
    [
        (r"\sqrt[3]{x-4}=3", "31"),
        (r"\sqrt[3]{x+2}=4", "62"),
        (r"\sqrt[5]{5x-2}=-2", "-6"),
        (r"\sqrt[7]{-3x+5}=2", "-41"),
        (r"\sqrt[9]{7-2x}=-1", "4"),
    ],
)
def test_any_odd_degree_and_both_affine_orderings_are_computed(formula: str, answer: str) -> None:
    plan = build_repair_plan(formula)
    assert plan.answer == answer
    assert f"x={answer}" in plan.solution_html


def test_parent_and_repair_child_have_different_values_and_parent_style() -> None:
    parent = build_context_repair_plan(_context(r"\sqrt[3]{x-4}=3", "31"))
    child = build_context_repair_plan(_context(r"\sqrt[3]{x+2}=4"))
    assert parent.answer == "31"
    assert child.answer == "62"
    assert "Возведём обе части уравнения в 3-ю степень" in child.solution_html
    assert r"x+2=64\iff x=62" in child.solution_html


@pytest.mark.parametrize("formula", [r"\sqrt[2]{x-4}=3", r"\sqrt[1]{x-4}=3", r"\sqrt[3]{x+2}=\frac{1}{2}", r"\sqrt[3]{x+y}=3"])
def test_unsupported_forms_fail_closed(formula: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(formula))
