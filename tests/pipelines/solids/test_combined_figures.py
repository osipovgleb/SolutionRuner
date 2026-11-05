"""Check exact source bytes, native roles, duplicate cleanup and reviewed restorations."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from combined_source_cases import CASES, GROUPS, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.combined_sources import (
    DATA,
    SOURCES,
    source_bytes,
)


def remove_diagrams(context):
    context["normalized_content"]["assets"] = []
    for s in context["normalized_content"]["sections"]:
        soup = BeautifulSoup(s["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        s["html"], s["asset_keys"] = str(soup), []


def swap_source(context, source):
    for a in context["normalized_content"]["assets"]:
        a["asset_id"], a["url"] = source, "/assets/" + source
    for s in context["normalized_content"]["sections"]:
        soup = BeautifulSoup(s["html"], "html.parser")
        for image in soup.find_all("img"):
            image["data-asset-id"], image["src"] = source, "/assets/" + source
        s["html"] = str(soup)


@pytest.mark.parametrize("source", SOURCES)
def test_exact_reviewed_source_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert (
        raw.startswith(b"\x89PNG")
        if SOURCES[source][0].endswith(".png")
        else b"<svg" in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_roles_and_single_diagram_after_stable_replay(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    n = ctx["normalized_content"]
    images = [
        (s["key"], im)
        for s in n["sections"]
        for im in BeautifulSoup(s["html"], "html.parser").find_all("img")
    ]
    assert len(images) == len(n["assets"]) == 1
    for s in n["sections"]:
        assert [
            im["data-asset-key"]
            for im in BeautifulSoup(s["html"], "html.parser").find_all("img")
        ] == s["asset_keys"]
    for a in case["context"]["normalized_content"]["assets"]:
        expected = DATA["corrections"].get(a["asset_id"], a["asset_id"])
        assert n["assets"][0]["asset_id"] == expected
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", GROUPS)
def test_another_solid_or_inscription_is_rejected(group):
    case = next(c for c in CASES if c["task"] == group)
    m = read(case)
    scene = DATA["scenes"].get(m.kind, m.kind)
    other = next(src for src, f in DATA["figures"].items() if f["scene"] != scene)
    ctx = deepcopy(case["context"])
    swap_source(ctx, other)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ["324458", "25837", "73015"])
def test_native_solution_only_figure_does_not_gain_a_duplicate_condition(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    replay(ctx, plan(case, ctx).transformations)
    assert not section(ctx, "condition")["asset_keys"]
    assert section(ctx, "solution")["asset_keys"] == ["image_1"]


@pytest.mark.parametrize("task", ["325643", "325645"])
def test_duplicate_native_reference_is_retained_only_in_condition(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    original = deepcopy(section(ctx, "condition"))
    replay(ctx, plan(case, ctx).transformations)
    assert section(ctx, "condition") == original
    assert section(ctx, "solution")["asset_keys"] == []
    damaged = deepcopy(case["context"])
    section(damaged, "solution")["html"] = section(damaged, "solution")["html"].replace(
        "/assets/fa2fd65b", "/assets/foreign-fa2fd65b"
    )
    with pytest.raises(ContentPlanError):
        plan(case, damaged)


@pytest.mark.parametrize("task", ["73329", "73331"])
def test_restored_hole_diagram_is_bound_to_reviewed_source_condition(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    original = BeautifulSoup(
        section(ctx, "condition")["html"], "html.parser"
    ).get_text()
    replay(ctx, plan(case, ctx).transformations)
    assert (
        BeautifulSoup(section(ctx, "condition")["html"], "html.parser").get_text()
        == original
    )
    assert (
        ctx["normalized_content"]["assets"][0]["asset_id"]
        == "13b3a337-2866-4c65-adcb-3002f0148f6d"
    )
    for field in ("identity", "condition"):
        changed = deepcopy(case["context"])
        if field == "identity":
            changed["problem_id"] = "foreign"
        else:
            section(changed, "condition")["html"] += " "
        with pytest.raises(ContentPlanError):
            plan(case, changed)


def test_other_missing_hole_diagrams_require_review():
    case = next(c for c in CASES if c["task"] == "27075")
    ctx = deepcopy(case["context"])
    remove_diagrams(ctx)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_nested_cone_source_is_replaced_with_reviewed_cylinder_cone_scene():
    case = next(c for c in CASES if c["task"] == "269369")
    ctx = deepcopy(case["context"])
    replay(ctx, plan(case, ctx).transformations)
    assert section(ctx, "condition") == section(case["context"], "condition")
    assert (
        ctx["normalized_content"]["assets"][0]["asset_id"]
        == "2d3cda98-18f9-4242-9a9c-34495d044b5b"
    )
    assert section(ctx, "solution")["asset_keys"] == ["image_1"]


def test_unexpected_generated_diagram_is_rejected():
    case = CASES[0]
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=({"asset_key": "foreign"},))
