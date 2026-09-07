"""Coverage for the base-EGE linear-equation group 509214."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.group_509214_planner import (
    RULE,
    UnsupportedCondition,
    build_context_repair_plan,
    build_repair_plan,
)


PARENT_FORMULA = "2+9x=4x+3"
PARENT_CONDITION = (
    '<p>Най\u00adди\u00adте ко\u00adрень урав\u00adне\u00adния '
    '<span data-inline-latex="2+9x=4x+3"></span>.</p>'
)
PARENT_SOLUTION = (
    '<p>По\u00adсле\u00adдо\u00adва\u00adтельно по\u00adлу\u00adча\u00adем:</p>'
    '<center><p><span data-inline-latex="'
    r'2+9x=4x+3\iff 9x-4x=3-2\iff 5x=1\iff x=0{,}2'
    '"></span>.</p></center>'
)


def _context(
    formula: str,
    *,
    answer: str | None = None,
    solution: str | None = None,
    condition_html: str | None = None,
) -> dict:
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "title": "Условие",
            "asset_keys": [],
            "html": condition_html
            or (
                '<p>Най\u00adди\u00adте ко\u00adрень урав\u00adне\u00adния '
                f'<span data-inline-latex="{formula}"></span>.</p>'
            ),
        }
    ]
    if answer is not None:
        sections.append(
            {
                "key": "answer",
                "section_id": "answer:1",
                "transformation_target_id": "section:answer:1",
                "title": "Ответ",
                "asset_keys": [],
                "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            }
        )
    if solution is not None:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
                "title": "Решение",
                "asset_keys": [],
                "html": solution,
            }
        )
    return {
        "problem_id": "050289a0-8e09-4ada-81f2-ad1c2bc08395",
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": sections,
        },
    }


def _targets(plan) -> dict[str, dict]:
    return {item["transformation_target_id"]: item for item in plan.transformations}


def _solution_target(targets: dict[str, dict]) -> dict:
    return targets.get("section:solution:1") or targets["section:solution"]


def _materialize(context: dict, plan) -> dict:
    result = deepcopy(context)
    sections = result["normalized_content"]["sections"]
    for item in plan.transformations:
        target = item["transformation_target_id"]
        key = target.split(":")[1]
        section = next((candidate for candidate in sections if candidate["key"] == key), None)
        if section is None:
            sections.append(
                {
                    "key": key,
                    "section_id": f"{key}:1",
                    "transformation_target_id": f"section:{key}:1",
                    **deepcopy(item["value"]),
                }
            )
        else:
            section.update(deepcopy(item["value"]))
    return result


def test_parent_matches_the_frozen_parent_style() -> None:
    context = _context(PARENT_FORMULA, answer="0,2", solution=PARENT_SOLUTION)

    plan = build_context_repair_plan(context)

    assert plan.answer == "0,2"
    assert plan.transformations == ()
    assert build_repair_plan(PARENT_FORMULA).solution_html == PARENT_SOLUTION


def test_group_is_registered_with_the_base_ege_scope() -> None:
    profile = get_group_profile("509214")
    handler = get_handler(RULE)

    assert profile.catalog_snapshot_id == "4073fc7b-2056-4697-b18b-38741c94d0f4"
    assert profile.snapshot_theme_id == "6eaa6630-cb99-478d-9fa1-f4ff94c85a76"
    assert profile.source_group_id == "f23c746f-e0e5-4598-9f07-416be328b49c"
    assert profile.category_key == "17"
    assert profile.content_rule_key == RULE
    assert profile.existing_solution_policy == "rewrite"
    assert handler.target.endswith("group_509214_planner:build_context_repair_plan")
    assert handler.requires_parent_condition_asset is False


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("2+9x=4x+3", "0,2"),
        ("-4+3x=8x+5", "-1,8"),
        ("-1+5x=10x+8", "-1,8"),
        ("-1+2x=10x+3", "-0,5"),
        ("6-2x=3x-10", "3,2"),
        ("-3+6x=-4x+4", "0,7"),
        ("4-2x=-4x+5", "0,5"),
        ("-6-4x=-8x+7", "3,25"),
        ("10x+3=10-4x", "0,5"),
        ("8-5x=5x-4", "1,2"),
        ("10-6x=9x+4", "0,4"),
        ("6x-3=4-4x", "0,7"),
    ],
)
def test_audited_group_forms_use_one_parent_style(formula: str, expected: str) -> None:
    plan = build_context_repair_plan(_context(formula))
    targets = _targets(plan)

    assert plan.answer == expected
    assert _solution_target(targets)["value"]["html"].startswith(
        "<p>По\u00adсле\u00adдо\u00adва\u00adтельно по\u00adлу\u00adча\u00adем:</p>"
    )
    assert f"x={expected.replace(',', '{,}')}" in _solution_target(targets)["value"]["html"]


def test_wrong_answer_and_existing_solution_are_repaired_to_parent_style() -> None:
    context = _context(
        "-1+5x=10x+8",
        answer="-1,4",
        solution="<p>Старое решение.</p>",
    )

    plan = build_context_repair_plan(context)
    targets = _targets(plan)

    assert plan.answer == "-1,8"
    assert targets["section:answer:1"]["value"]["html"] == (
        '<p><span data-effect="spaced">-1,8</span></p>'
    )
    assert r"-1+5x=10x+8\iff 5x-10x=8+1\iff -5x=9\iff x=-1{,}8" in targets[
        "section:solution:1"
    ]["value"]["html"]


def test_repaired_content_converges() -> None:
    context = _context("6-2x=3x-10", answer=".")

    first_plan = build_context_repair_plan(context)
    repaired = _materialize(context, first_plan)

    assert build_context_repair_plan(repaired).transformations == ()


@pytest.mark.parametrize(
    "formula",
    [
        "2+9x=4+3",
        "2+3x=4x+3x",
        "2+5x=2x+3",
        r"2+\\frac{9}{1}x=4x+3",
    ],
)
def test_unsupported_forms_fail_closed(formula: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(formula))


def test_condition_markup_with_asset_fails_closed() -> None:
    context = _context(PARENT_FORMULA)
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})

    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context)
