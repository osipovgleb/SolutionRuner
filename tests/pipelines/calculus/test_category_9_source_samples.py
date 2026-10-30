"""Live analytic calculus questions: exact answers and complete-input refusal."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads((Path(__file__).parent / "fixtures/category_9_text.json").read_text())
CASES = DATA["cases"]
SUPPORTED = CASES


def plan(case, context):
    return get_handler(get_group_profile(case["group"]).content_rule_key).plan(
        PlanInput(context)
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_live_group_selects_the_existing_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.category_key == "9"
    assert profile.content_rule_key == group["rule"]


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
def test_source_values_match_an_independent_plan_without_mutating_input(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    answer = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    soup = BeautifulSoup(answer, "html.parser")
    for tag in soup.select("[data-inline-latex]"):
        tag.replace_with(tag["data-inline-latex"])
    expected = parse_rational(
        case.get("verified_answer", soup.get_text("", strip=True).removesuffix("."))
    )
    result = plan(case, context)
    assert parse_rational(result.answer) == expected
    assert context == original
    allowed = (
        ("section:solution", "section:answer", "section:condition")
        if case.get("condition_repair")
        else ("section:solution", "section:answer")
    )
    assert all(
        t["transformation_target_id"].startswith(allowed)
        for t in result.transformations
    )
    html = "".join(t["value"].get("html", "") for t in result.transformations)
    assert "это задание первой части" not in html


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
def test_stored_answer_is_not_used_to_calculate_the_result(case):
    context = deepcopy(case["context"])
    expected = plan(case, context).answer
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>123456789</p>"
    assert plan(case, context).answer == expected


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
def test_prepared_content_is_idempotent(case):
    context = deepcopy(case["context"])
    first = plan(case, context)
    sections = context["normalized_content"]["sections"]
    for t in first.transformations:
        section = next(
            (
                s
                for s in sections
                if s.get("transformation_target_id") == t["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            key = t["transformation_target_id"].split(":")[1]
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(section)
        section.update(t["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [False, True])
def test_extra_instructions_cannot_be_discarded(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>В ответе удвойте полученное значение.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    original = deepcopy(context)
    with pytest.raises(ValueError):
        plan(case, context)
    assert context == original


@pytest.mark.parametrize(
    "extra", ["<p>+ 3</p>", "<script>doubleAnswer()</script>", "<p>&#65520;</p>"]
)
def test_unparsed_arithmetic_or_active_markup_is_not_invisible(extra):
    case = SUPPORTED[0]
    context = deepcopy(case["context"])
    condition = context["normalized_content"]["sections"][0]
    condition["html"] += extra
    with pytest.raises(ValueError):
        plan(case, context)
