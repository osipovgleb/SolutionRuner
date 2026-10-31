"""Campaign sources reuse graph rules, exact figures and both parent methods."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import (
    diagrams,
    fractional_hyperbola,
    unshifted_hyperbola,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_hyperbolas.json").read_text()
)
CASES = DATA["cases"]


def plan(case, context=None, *, data=None, mime="image/svg+xml"):
    rule = get_group_profile(case["group"]).content_rule_key
    prepared = _with_required_assets(
        case["context"] if context is None else context, rule
    )
    return get_handler(rule).plan(
        PlanInput(
            prepared,
            condition_asset_bytes=(ROOT / case["condition_file"]).read_bytes()
            if data is None
            else data,
            current_asset_content_type=mime,
        )
    )


def replay(context, transformations):
    result = deepcopy(context)
    content = result["normalized_content"]
    for change in transformations:
        assert change["transformation_target_id"].startswith("section:")
        key = change["transformation_target_id"].split(":")[1]
        section = next((s for s in content["sections"] if s["key"] == key), None)
        if section is None:
            section = {"key": key, "section_id": key + ":1"}
            content["sections"].append(section)
        section.update(change["value"])
    return result


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_seven_profiles_reuse_the_registered_graph_rules(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.category_key == "12" and profile.content_rule_key == group["rule"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_compute_without_saved_answers_or_solution_evidence(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    result = plan(case, context)
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    assert context == original and not result.warnings
    for section in context["normalized_content"]["sections"]:
        if section["key"] in {"answer", "solution"}:
            section["html"] = "<p>999999999</p>"
    assert plan(case, context).answer == result.answer
    updated = replay(original, result.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    condition = lambda c: (
        BeautifulSoup(
            next(
                s["html"]
                for s in c["normalized_content"]["sections"]
                if s["key"] == "condition"
            ),
            "html.parser",
        ).img
    )
    assert condition(updated) == condition(original)
    html = next(
        s["html"]
        for s in updated["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    methods = BeautifulSoup(html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(methods) == 2
    assert methods[0].img is not None and methods[1].img is not None
    assert "Альтернативное решение" == methods[1]["data-solution-title"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mode", ["leading", "trailing", "extra_math", "extra_image", "wrong_image"]
)
def test_complete_conditions_and_image_identity_cannot_ignore_changes(case, mode):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mode in {"leading", "trailing"}:
        extra = "<p>Ответ округлите до целого числа.</p>"
        condition["html"] = (
            extra + condition["html"]
            if mode == "leading"
            else condition["html"] + extra
        )
    elif mode == "extra_math":
        condition["html"] += '<span data-inline-latex="x=1"></span>'
    elif mode == "extra_image":
        condition["html"] += '<img src="/assets/foreign"/>'
    else:
        soup = BeautifulSoup(condition["html"], "html.parser")
        soup.img["src"] = "/assets/foreign"
        condition["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_graph_bytes_are_the_exact_inspected_source_and_drift_fails_closed(case):
    data = (ROOT / case["condition_file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == case["condition_sha256"]
    with pytest.raises(ContentPlanError):
        plan(case, data=data + b" ")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_geometry_is_unchanged_and_figures_match_their_registered_checksums(
    case,
):
    rule = get_group_profile(case["group"]).content_rule_key
    module = (
        fractional_hyperbola
        if "fractional" in rule
        else unshifted_hyperbola
        if "unshifted" in rule
        else diagrams
    )
    aid = next(
        a["asset_id"]
        for a in case["context"]["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    entry = module.registry()["conditions"][aid]
    figures = (
        module.registry()["graphs"][entry["graph_key"]] if module is diagrams else entry
    )
    source = (ROOT / case["condition_file"]).read_bytes()
    for method in ("points", "offset"):
        figure = figures[method]
        svg = (module.ASSET_DIR / figure["file"]).read_bytes()
        assert hashlib.sha256(svg).hexdigest() == figure["sha256"]
        role = (
            "hyperbola-solution-overlay"
            if module is diagrams
            else "fractional-hyperbola-overlay"
            if module is fractional_hyperbola
            else "unshifted-hyperbola-overlay"
        )
        # Overlays are the only added nodes; every original byte is retained.
        begin = svg.index(('<g data-role="' + role + '">').encode())
        end = svg.index(b"</g>", begin) + len(b"</g>")
        assert svg[:begin] + svg[end:] == source
