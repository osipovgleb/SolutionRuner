"""Independent source answers and invariants for prepared probability families."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads((Path(__file__).parent / "fixtures/category_5.json").read_text())
GROUPS = {group["key"]: group for group in DATA["groups"]}
CASES = DATA["cases"]


def _plan(case, context):
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    generated = tuple(
        {
            "asset_key": spec["asset_key"],
            "sha256": spec["sha256"],
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(context)
    )
    return handler.plan(
        PlanInput(
            context,
            parent_solution_html=GROUPS[case["group"]]["parent_solution_html"],
            generated_solution_assets=generated,
        )
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda group: group["key"])
def test_live_catalog_identity_selects_the_audited_shared_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.category_key == "5"
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.content_rule_key == group["rule"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_source_answer_and_input_are_preserved_independently(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    source_answer = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    soup = BeautifulSoup(source_answer, "html.parser")
    for span in soup.select("span[data-inline-latex]"):
        span.replace_with(span["data-inline-latex"])
    source_text = soup.get_text("", strip=True)
    expected = [
        parse_rational(token.removesuffix(".")) for token in source_text.split("|")
    ]
    plan = _plan(case, context)
    if case["task"] == "704601":
        assert source_text == "0,081"
        assert parse_rational(plan.answer) == parse_rational("0,0081")
    else:
        assert parse_rational(plan.answer) in expected
    assert context == original
    solution = BeautifulSoup(plan.solution_html, "html.parser")
    keys = [img["data-asset-key"] for img in solution.find_all("img")]
    added = set()
    for change in plan.transformations:
        if change["transformation_target_id"].startswith("asset:"):
            assert change["operation"] == "add"
            added.add(change["value"]["asset_key"])
            assert change["value"]["asset_id"].startswith("preview-")
            continue
        assert change["value"]["asset_keys"] == (
            keys
            if change["transformation_target_id"].startswith("section:solution")
            else []
        )
    assert set(keys) <= added | {
        a["asset_key"] for a in context["normalized_content"]["assets"]
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_a_wrong_stored_answer_does_not_change_the_computation(case):
    context = deepcopy(case["context"])
    expected = _plan(case, context).answer
    answer = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "answer"
    )
    answer["html"] = "<p>1234567</p>"
    plan = _plan(case, context)
    assert plan.answer == expected
    assert any(
        t["transformation_target_id"] == answer["transformation_target_id"]
        for t in plan.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_prepared_content_is_idempotent(case):
    context = deepcopy(case["context"])
    first = _plan(case, context)
    sections = context["normalized_content"]["sections"]
    for change in first.transformations:
        if change["transformation_target_id"].startswith("asset:"):
            context["normalized_content"]["assets"].append(
                {
                    **change["value"],
                    "transformation_target_id": change["transformation_target_id"],
                }
            )
            continue
        section = next(
            (
                s
                for s in sections
                if s["transformation_target_id"] == change["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            assert change["operation"] == "add"
            key = change["transformation_target_id"].removeprefix("section:")
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": change["transformation_target_id"],
            }
            sections.append(section)
        section.update(change["value"])
    assert _plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
@pytest.mark.parametrize("leading", [False, True], ids=["suffix", "prefix"])
def test_unknown_instruction_fails_without_mutating_input(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    instruction = "<p>В ответе запишите удвоенную вероятность.</p>"
    condition["html"] = (
        instruction + condition["html"] if leading else condition["html"] + instruction
    )
    original = deepcopy(context)
    with pytest.raises(ValueError):
        _plan(case, context)
    assert context == original
