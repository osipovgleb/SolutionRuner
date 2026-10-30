"""Live catalog examples, immutable inputs and fail-closed coordinate questions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads((Path(__file__).parent / "fixtures/category_2.json").read_text())
CASES = DATA["cases"]


def plan(case, context):
    profile = get_group_profile(case["group"])
    return get_handler(profile.content_rule_key).plan(PlanInput(context))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_live_group_identity_selects_the_registered_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.category_key == "2"
    assert profile.content_rule_key == group["rule"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answer_matches_an_independent_plan(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    answer = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    soup = BeautifulSoup(answer, "html.parser")
    for s in soup.select("[data-inline-latex]"):
        s.replace_with(s["data-inline-latex"])
    expected = parse_rational(soup.get_text("", strip=True).removesuffix("."))
    result = plan(case, context)
    assert parse_rational(result.answer) == expected
    assert context == original
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in result.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_answer_is_not_an_input_to_the_computation(case):
    context = deepcopy(case["context"])
    expected = plan(case, context).answer
    answer = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "answer"
    )
    answer["html"] = "<p>1234567</p>"
    assert plan(case, context).answer == expected


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_prepared_vector_content_is_idempotent(case):
    context = deepcopy(case["context"])
    first = plan(case, context)
    sections = context["normalized_content"]["sections"]
    for change in first.transformations:
        section = next(
            (
                s
                for s in sections
                if s["transformation_target_id"] == change["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            key = change["transformation_target_id"].split(":")[1]
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": change["transformation_target_id"],
            }
            sections.append(section)
        section.update(change["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [False, True])
def test_unknown_instruction_is_never_discarded(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    instruction = "<p>В ответе удвойте полученное значение.</p>"
    condition["html"] = (
        instruction + condition["html"] if leading else condition["html"] + instruction
    )
    original = deepcopy(context)
    with pytest.raises(ValueError):
        plan(case, context)
    assert context == original
