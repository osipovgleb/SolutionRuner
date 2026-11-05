"""Verify native prism diagram bytes, retained roles and compatible restoration of second images."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from prism_source_cases import CASES, GROUPS, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_sources import SOURCES, source_bytes
from solution_runner.pipelines.triangles.isosceles.side_altitude_figures import (
    condition_changes,
)


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_exact_source_svg(source):
    raw = source_bytes(source)
    assert (
        hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
        and b"<svg" in raw
        and b"<image" not in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_figure_id_and_each_section_role_are_preserved(case):
    ctx = deepcopy(case["context"])
    before = ctx["normalized_content"]
    result = plan(case, ctx)
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    assert not any(
        t["operation"] == "remove"
        and t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    original = deepcopy(before)
    replay(ctx, result.transformations)
    after = ctx["normalized_content"]
    for a in original["assets"]:
        assert a in after["assets"]
        role = next(
            s["key"] for s in original["sections"] if a["asset_key"] in s["asset_keys"]
        )
        assert a["asset_key"] in section(ctx, role)["asset_keys"]
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "task", ["27057", "27062", "27082", "27104", "27183", "324451", "516250", "324457"]
)
@pytest.mark.parametrize("change", ["foreign", "url", "duplicate", "wrong_object"])
def test_unreviewed_or_foreign_figures_are_rejected(task, change):
    c = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(c["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if change == "foreign":
        a["asset_id"] = "foreign"
    elif change == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif change == "duplicate":
        assets.append(deepcopy(a))
    else:
        other = "c66e1981-92e4-42b7-9357-575a61145152"
        a["asset_id"] = other
        a["url"] = "/assets/" + other
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                if img["data-asset-key"] == a["asset_key"]:
                    img["data-asset-id"] = other
                    img["src"] = "/assets/" + other
            s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


@pytest.mark.parametrize("task", ["27104", "324457", "516250"])
def test_missing_second_solution_drawing_is_restored_without_duplicate_source(task):
    c = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(c["context"])
    n = ctx["normalized_content"]
    n["assets"] = [a for a in n["assets"] if a["asset_key"] != "image_2"]
    s = section(ctx, "solution")
    soup = BeautifulSoup(s["html"], "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    s["html"] = str(soup)
    s["asset_keys"] = []
    result = plan(c, ctx)
    assert any(
        t["transformation_target_id"] == "asset:image_2" and t["operation"] == "add"
        for t in result.transformations
    )
    replay(ctx, result.transformations)
    assert (
        "image_2" in section(ctx, "solution")["asset_keys"]
        and plan(c, ctx).transformations == ()
    )


def test_legacy_helper_cleanup_default_and_explicitly_preserved_second_asset():
    c = next(c for c in CASES if c["task"] == "324457")
    ctx = c["context"]
    current = next(
        a for a in ctx["normalized_content"]["assets"] if a["asset_key"] == "image_1"
    )
    args = (
        ctx,
        section(ctx, "condition"),
        current,
        "image_1",
        current["asset_id"],
        current["url"],
    )
    assert {
        "transformation_target_id": "asset:image_2",
        "operation": "remove",
    } in condition_changes(*args)
    assert condition_changes(*args, preserve_assets=("image_2",)) == ()


def test_highlighted_pyramid_must_match_actual_vertices():
    c = next(c for c in CASES if c["task"] == "516250")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    assert "B_1" in s["html"]
    s["html"] = s["html"].replace('data-inline-latex="B_1"', 'data-inline-latex="C_1"')
    with pytest.raises(ContentPlanError):
        plan(c, ctx)
