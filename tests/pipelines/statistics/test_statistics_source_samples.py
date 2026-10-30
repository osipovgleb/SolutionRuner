"""Independent source answers and invariants for prepared statistics families."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads((Path(__file__).parent / "fixtures/category_6.json").read_text())
GROUPS = {group["key"]: group for group in DATA["groups"]}
CASES = DATA["cases"]


def _plan(case, context):
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    condition_bytes = None
    if handler.requires_condition_asset_download:
        content = context["normalized_content"]
        condition = next(s for s in content["sections"] if s["key"] == "condition")
        asset = next(
            a for a in content["assets"] if a["asset_key"] in condition["asset_keys"]
        )
        from solution_runner.pipelines.statistics import euler

        condition_bytes = (
            Path(euler.__file__).with_name("assets") / (asset["asset_id"] + ".svg")
        ).read_bytes()
    return handler.plan(
        PlanInput(
            context,
            parent_solution_html=GROUPS[case["group"]]["parent_solution_html"],
            condition_asset_bytes=condition_bytes,
        )
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda group: group["key"])
def test_live_catalog_identity_selects_the_audited_shared_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.category_key == "6"
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
    expected = parse_rational(source_text.removesuffix("."))
    plan = _plan(case, context)
    exact = {"663480": r"\frac{\sqrt{3}}{3}", "663481": r"\frac{\sqrt{6}}{12}"}
    if case["task"] in exact:
        assert plan.answer == exact[case["task"]]
        assert source_text in ("0,58", "0,2")
    else:
        assert parse_rational(plan.answer) == expected
    assert context == original
    solution = BeautifulSoup(plan.solution_html, "html.parser")
    keys = [img["data-asset-key"] for img in solution.find_all("img")]
    for change in plan.transformations:
        assert change["value"]["asset_keys"] == (
            keys
            if change["transformation_target_id"].startswith("section:solution")
            else []
        )
    assert set(keys) <= {
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
