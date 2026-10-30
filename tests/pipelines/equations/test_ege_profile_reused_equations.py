"""Audited source samples for shared elementary-equation rules."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import (
    all_group_profiles,
    get_group_profile,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

CASES = json.loads(
    (Path(__file__).parent / "fixtures/ege_profile_reused_equations.json").read_text()
)
RULE_CASES = list(
    {get_group_profile(case["group"]).content_rule_key: case for case in CASES}.values()
)


def test_all_category_seven_groups_have_verified_source_identities():
    groups = json.loads(
        (
            Path(__file__).parent / "fixtures/ege_profile_category_7_groups.json"
        ).read_text()
    )
    assert len(groups) == 64
    assert {case["group"] for case in CASES} == {group["key"] for group in groups}
    assert {
        profile.group_key
        for profile in all_group_profiles().values()
        if profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        and profile.category_key == "7"
    } == {group["key"] for group in groups}
    for group in groups:
        profile = get_group_profile(group["key"])
        assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        assert profile.category_key == "7"
        assert profile.source_group_id == group["uuid"]
        assert profile.snapshot_theme_id == group["theme_uuid"]
        assert profile.group_order_index == group["order"]
        assert profile.theme_order_index == group["theme_order"]


@pytest.mark.parametrize("case", RULE_CASES, ids=lambda case: case["group"])
def test_unknown_leading_instruction_is_not_ignored(case):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        "<p>В ответе запишите удвоенное значение.</p>" + condition["html"]
    )
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    with pytest.raises(ValueError):
        handler.plan(PlanInput(context))


def _source_answer(html):
    soup = BeautifulSoup(html, "html.parser")
    for span in soup.select("span[data-inline-latex]"):
        span.replace_with(span["data-inline-latex"])
    value = soup.get_text("", strip=True)
    return re.sub(r"\\frac\{-(\d+)\}\{(\d+)\}", r"-\\frac{\1}{\2}", value)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_source_samples_compute_answers_without_mutating_input(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    sections = context["normalized_content"]["sections"]
    answer = next(section for section in sections if section["key"] == "answer")
    expected = _source_answer(answer["html"])

    plan = handler.plan(PlanInput(context))

    assert parse_rational(plan.answer) == parse_rational(expected)
    assert context == original
    assert not handler.requires_parent_condition_asset
    available = {
        asset["asset_key"] for asset in context["normalized_content"]["assets"]
    }
    assert all(
        set(change["value"]["asset_keys"]) <= available
        for change in plan.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_source_answer_is_not_used_to_compute_result(case):
    context = deepcopy(case["context"])
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    expected = handler.plan(PlanInput(context)).answer
    answer = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "answer"
    )
    answer["html"] = "<p>123456789</p>"

    plan = handler.plan(PlanInput(context))

    assert plan.answer == expected
    assert any(
        t["transformation_target_id"] == answer["transformation_target_id"]
        for t in plan.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_unsupported_formula_fails_without_mutating_input(case):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        '<p>Решите уравнение <span data-inline-latex="x^{x}=7"></span>.</p>'
    )
    original = deepcopy(context)
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)

    with pytest.raises(ValueError):
        handler.plan(PlanInput(context))

    assert context == original


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_unrecognized_instruction_is_not_silently_ignored(case):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] += "<p>В ответе запишите удвоенный корень.</p>"
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)

    with pytest.raises(ValueError):
        handler.plan(PlanInput(context))


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        (r"\frac{1}{-x+6}=1", "5"),
        (r"\frac{1}{0x+6}=1", None),
        (r"\frac{1}{3x+1}=\frac{1}{3}", None),
    ],
)
def test_reciprocal_equations_handle_negative_and_invalid_coefficients(
    formula, expected
):
    case = next(case for case in CASES if case["group"] == "504406")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        f'<p>Решите уравнение <span data-inline-latex="{formula}"></span>.</p>'
    )
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)

    if expected is None:
        with pytest.raises(ValueError):
            handler.plan(PlanInput(context))
    else:
        assert handler.plan(PlanInput(context)).answer == expected


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_prepared_content_is_idempotent(case):
    context = deepcopy(case["context"])
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    plan = handler.plan(PlanInput(context))
    sections = context["normalized_content"]["sections"]
    for change in plan.transformations:
        section = next(
            s
            for s in sections
            if s["transformation_target_id"] == change["transformation_target_id"]
        )
        section.update(change["value"])

    assert handler.plan(PlanInput(context)).transformations == ()
