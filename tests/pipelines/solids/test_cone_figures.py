"""Check original cone image bytes, child-specific roles and required vessel orientation."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from cone_source_cases import CASES, GROUPS, plan
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.cone_sources import SOURCES, source_bytes


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_source_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert (
        raw.startswith(b"\x89PNG\r\n\x1a\n")
        if SOURCES[source][0].endswith(".png")
        else b"<svg" in raw and b"<image" not in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_figure_ids_and_roles_are_preserved(case):
    before = case["context"]["normalized_content"]
    ctx = deepcopy(case["context"])
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    replay(ctx, plan(case, ctx).transformations)
    after = ctx["normalized_content"]
    for asset in before["assets"]:
        assert asset in after["assets"]
        role = next(
            s["key"]
            for s in before["sections"]
            if asset["asset_key"] in s["asset_keys"]
        )
        assert asset["asset_key"] in section(ctx, role)["asset_keys"]
        if role == "condition":
            assert section(ctx, "condition") == section(case["context"], "condition")
    assert len(after["assets"]) == 1


@pytest.mark.parametrize(
    "task", ["27052", "27093", "74257", "27121", "27122", "318145", "324453"]
)
@pytest.mark.parametrize("change", ["foreign", "url", "duplicate", "wrong_object"])
def test_unreviewed_or_incompatible_drawings_are_rejected(task, change):
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
        other = (
            "c66e1981-92e4-42b7-9357-575a61145152"
            if task in {"27052", "27121", "27122", "318145", "324453"}
            else "d97c3614-2d40-4659-aaac-24ddd93dd314"
        )
        a["asset_id"] = other
        a["url"] = "/assets/" + other
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                img["data-asset-id"] = other
                img["src"] = "/assets/" + other
            s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


@pytest.mark.parametrize("task", ["318145", "318147", "505123", "505380"])
def test_vessel_orientation_cannot_be_inferred_without_its_figure(task):
    c = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    soup.img.decompose()
    s["html"] = str(soup)
    s["asset_keys"] = []
    ctx["normalized_content"]["assets"] = []
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_numbered_slant_figure_cannot_silently_keep_wrong_labels():
    c = next(c for c in CASES if c["task"] == "74257")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    assert "44" in s["html"]
    s["html"] = s["html"].replace("44", "42")
    with pytest.raises(ContentPlanError):
        plan(c, ctx)
