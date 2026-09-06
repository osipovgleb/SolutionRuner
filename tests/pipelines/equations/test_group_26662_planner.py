"""Strict group-26662 coverage from the parent and one real repair child."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_26662_planner import (
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.equations.group_26663_planner import (
    RULE as NEGATIVE_RULE,
    build_repair_plan as build_negative_repair_plan,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)


PARENT_ID = "20bfb2f5-1f08-40f0-b0e5-e678c7fbea3e"
CHILD_ID = "8be7f38e-7bc4-42a6-8bd0-6d245c63251d"


def _formula(numerator: int, denominator: int, whole: int, part_numerator: int, part_denominator: int) -> str:
    return rf"\frac{{{numerator}}}{{{denominator}}}x={whole}\frac{{{part_numerator}}}{{{part_denominator}}}"


def _condition_html(formula: str, *, split_formula_from_paragraph: bool = False) -> str:
    prefix = "Най­ди­те ко­рень урав­не­ния: "
    span = f'<span data-inline-latex="{formula}"></span>.'
    if split_formula_from_paragraph:
        return f"<p>{prefix}</p> {span}"
    return f"<p>{prefix}{span}</p>"


def _context(
    problem_id: str,
    formula: str,
    *,
    answer: str | None,
    solution: str | None = None,
    split_formula_from_paragraph: bool = False,
) -> dict:
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "title": "Условие",
            "asset_keys": [],
            "html": _condition_html(formula, split_formula_from_paragraph=split_formula_from_paragraph),
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
        "problem_id": problem_id,
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": sections,
        },
    }


PARENT = _context(PARENT_ID, _formula(4, 7, 7, 3, 7), answer="13")
REPAIR_CHILD = _context(
    CHILD_ID,
    _formula(8, 9, 4, 4, 9),
    answer="5",
    split_formula_from_paragraph=True,
)


def _plan(context: dict):
    return build_repair_plan(context, parent_condition_asset_id=None)


def test_empty_runtime_asset_id_is_equivalent_to_no_asset() -> None:
    plan = build_repair_plan(deepcopy(REPAIR_CHILD), parent_condition_asset_id="")

    assert plan.answer == "5"


def _targets(plan) -> dict[str, dict]:
    return {item["transformation_target_id"]: item for item in plan.transformations}


def _materialize(context: dict, plan) -> dict:
    result = deepcopy(context)
    sections = result["normalized_content"]["sections"]
    for item in plan.transformations:
        key = item["transformation_target_id"].split(":")[1]
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


def test_profile_pins_group_scope_and_assetless_rule() -> None:
    profile = get_group_profile("26662")

    assert profile.source_group_id == "7077709e-38b6-4081-9b4c-d3a8af279740"
    assert profile.category_key == "7"
    assert profile.snapshot_theme_id == "f63e28de-a1e4-47c2-8ec6-b785c5319f0e"
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id is None
    assert profile.existing_solution_policy == "rewrite"


def test_real_repair_child_rejoins_formula_to_one_condition_paragraph() -> None:
    plan = _plan(deepcopy(REPAIR_CHILD))
    condition = _targets(plan)["section:condition:1"]["value"]["html"]
    solution = _targets(plan)["section:solution"]["value"]["html"]

    assert plan.answer == "5"
    assert condition == _condition_html(_formula(8, 9, 4, 4, 9))
    assert "</p> <span" not in condition
    assert "\n" not in condition
    assert r"\frac{8}{9}x=4\frac{4}{9}\iff \frac{8}{9}x=\frac{40}{9}\iff 8x=40\iff x=5" in solution
    assert r"\frac{4}{7}x=7\frac{3}{7}" not in solution


def test_second_audited_negative_form_preserves_signs_in_solution() -> None:
    context = _context("9679", r"-\frac{2}{5}x=-9\frac{1}{5}", answer="23")

    solution = _targets(_plan(context))["section:solution"]["value"]["html"]
    assert r"-\frac{2}{5}x=-9\frac{1}{5}\iff -\frac{2}{5}x=-\frac{46}{5}\iff -2x=-46\iff x=23" in solution


def test_group_26663_accepts_the_audited_negative_root() -> None:
    context = _context("9657", r"-\frac{5}{6}x=18\frac{1}{3}", answer="- 22", split_formula_from_paragraph=True)
    plan = build_negative_repair_plan(context, parent_condition_asset_id="")

    assert plan.answer == "-22"
    assert r"-\frac{5}{6}x=18\frac{1}{3}\iff -\frac{5}{6}x=\frac{55}{3}\iff -5x=110\iff x=-22" in _targets(plan)["section:solution"]["value"]["html"]
    assert _targets(plan)["section:condition:1"]["value"]["html"] == _condition_html(r"-\frac{5}{6}x=18\frac{1}{3}")


def test_group_26663_profile_is_explicit() -> None:
    profile = get_group_profile("26663")
    assert profile.source_group_id == "e11d0ef5-d850-4f7e-89a8-5d4ea865ceee"
    assert profile.content_rule_key == NEGATIVE_RULE


def test_parent_and_materialized_repair_converge() -> None:
    parent = _materialize(deepcopy(PARENT), _plan(deepcopy(PARENT)))
    assert _plan(parent).transformations == ()

    repaired = _materialize(deepcopy(REPAIR_CHILD), _plan(deepcopy(REPAIR_CHILD)))
    assert _plan(repaired).transformations == ()


@pytest.mark.parametrize("stored", [None, "", "-", "4", "5,0"])
def test_missing_malformed_and_wrong_answer_is_repaired(stored: str | None) -> None:
    context = _context("answer", _formula(8, 9, 4, 4, 9), answer=stored)

    answer = next(
        item["value"]["html"]
        for item in _plan(context).transformations
        if item["transformation_target_id"].startswith("section:answer")
    )
    assert answer == '<p><span data-effect="spaced">5</span></p>'


@pytest.mark.parametrize(
    "html",
    [
        _condition_html(_formula(8, 9, 4, 4, 9)).replace("Най­ди­те", "Укажите", 1),
        _condition_html(_formula(8, 9, 4, 4, 9)).replace(r"\frac{8}{9}", r"\frac{0}{9}"),
        _condition_html(_formula(8, 9, 4, 4, 9)).replace("<p>", '<p class="other">'),
        _condition_html(_formula(8, 9, 4, 4, 9)).replace("</p>", "<br/></p>"),
    ],
)
def test_unsupported_conditions_fail_closed(html: str) -> None:
    context = deepcopy(REPAIR_CHILD)
    context["normalized_content"]["sections"][0]["html"] = html

    with pytest.raises(RightTrianglePlanError):
        _plan(context)


def test_unexpected_asset_fails_closed() -> None:
    context = deepcopy(REPAIR_CHILD)
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})

    with pytest.raises(RightTrianglePlanError):
        _plan(context)
