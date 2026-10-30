"""Live catalog examples, immutable inputs and fail-closed coordinate questions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads((Path(__file__).parent / "fixtures/category_2.json").read_text())
CASES = DATA["cases"]


def plan(case, context):
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    context = _with_required_assets(context, profile.content_rule_key)
    generated = tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(context)
    )
    downloaded = None
    if handler.requires_condition_asset_download:
        asset = context["normalized_content"]["assets"][0]
        downloaded = (
            Path(__file__).parents[3]
            / "src/solution_runner/pipelines/vectors/assets"
            / (asset["asset_id"] + ".svg")
        ).read_bytes()
    return handler.plan(
        PlanInput(
            context,
            parent_asset_id=profile.condition_asset_id,
            current_asset_content_type="image/svg+xml"
            if context["normalized_content"].get("assets")
            else None,
            generated_solution_assets=generated,
            condition_asset_bytes=downloaded,
        )
    )


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
    expected = parse_rational(
        case.get("verified_answer", soup.get_text("", strip=True).removesuffix("."))
    )
    result = plan(case, context)
    assert parse_rational(result.answer) == expected
    assert context == original
    permitted = ("section:solution", "section:answer")
    if case["task"] in {"60955", "27727", "27728", "27729"}:
        permitted += ("asset:image_1", "section:condition")
    if case["task"] == "654463":
        permitted += ("asset:triangle_coordinates",)
    assert all(
        t["transformation_target_id"].startswith(permitted)
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
        if change["transformation_target_id"].startswith("asset:"):
            asset = (
                next(
                    a
                    for a in context["normalized_content"]["assets"]
                    if "asset:" + a["asset_key"] == change["transformation_target_id"]
                )
                if change["operation"] != "add"
                else {}
            )
            asset.update(change["value"])
            if change["operation"] == "add":
                context["normalized_content"]["assets"].append(asset)
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
