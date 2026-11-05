"""Check source bytes, unchanged native roles, named glyphs and numerical annotations."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from pyramid_source_cases import CASES, GROUPS, generated, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.pyramid_sources import DATA, SOURCES, source_bytes


@pytest.mark.parametrize("source", SOURCES)
def test_exact_reviewed_svg_bytes(source):
    raw = source_bytes(source)
    assert (
        hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
        and b"<svg" in raw
        and b"<image" not in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_each_native_source_and_original_role_is_preserved(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    for a in before["normalized_content"]["assets"]:
        assert a in ctx["normalized_content"]["assets"]
        role = next(
            s["key"]
            for s in before["normalized_content"]["sections"]
            if a["asset_key"] in s["asset_keys"]
        )
        assert a["asset_key"] in section(ctx, role)["asset_keys"]
    for s in ctx["normalized_content"]["sections"]:
        keys = [
            i["data-asset-key"]
            for i in BeautifulSoup(s["html"], "html.parser").find_all("img")
        ]
        assert keys == s["asset_keys"]
    drawings = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    assert len(drawings) == (
        1 if case["task"] in {"284679", "284919", "285039", "285279"} else 0
    )
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("field", ["asset_key", "sha256", "source_asset_id", "url"])
def test_generated_named_diagram_identity_is_strict(field):
    c = next(c for c in CASES if c["task"] == "284679")
    assets = list(generated(c, c["context"]))
    assets[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(c, generated_solution_assets=tuple(assets))


@pytest.mark.parametrize(
    "task",
    [
        "914",
        "27069",
        "27070",
        "27110",
        "27155",
        "27171",
        "27182",
        "245353",
        "284348",
        "284351",
        "284354",
    ],
)
@pytest.mark.parametrize("change", ["foreign", "url", "duplicate"])
def test_invalid_source_identity_rejected(task, change):
    c = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(c["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if change == "foreign":
        a["asset_id"] = "foreign"
    elif change == "url":
        a["url"] = "https://example.com/foreign.svg"
    else:
        assets.append(deepcopy(a))
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_numeric_solution_annotation_cannot_silently_follow_changed_dimensions():
    c = next(c for c in CASES if c["task"] == "76507")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    for node in list(soup.find_all(string=True)):
        if "14" in node:
            node.replace_with(str(node).replace("14", "16"))
    s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_floor_numeric_height_must_match_transcribed_svg():
    c = next(c for c in CASES if c["task"] == "269541")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    s["html"] = s["html"].replace("5.", "6.")
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_changed_midpoint_cannot_reuse_previous_named_drawing():
    c = next(c for c in CASES if c["task"] == "284351")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    s["html"] = s["html"].replace("R", "M")
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


@pytest.mark.parametrize(
    "task,source",
    [
        ("284679", "f7eb48c5-f8d0-484d-948c-78f5069e1968"),
        ("285039", "ecbfb007-8435-4873-aa42-8d483008bc19"),
    ],
)
def test_generated_letter_keeps_native_wireframe_and_unique_svg_ids(task, source):
    import xml.etree.ElementTree as ET

    c = next(c for c in CASES if c["task"] == task)
    drawing = get_handler(GROUPS[c["group"]]["rule"]).diagram_specs(c["context"])[0]
    original = ET.fromstring(source_bytes(source))
    generated = ET.fromstring(drawing["svg_text"])

    def wireframe(root):
        return [ET.tostring(n) for n in root if not n.tag.endswith("g")]

    assert wireframe(original) == wireframe(generated)
    ids = [n.get("id") for n in generated.iter() if n.get("id")]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("source", list(DATA["floor"]))
def test_numeric_transcription_must_match_exact_source_revision(source, monkeypatch):
    monkeypatch.setitem(DATA["floor"][source], "sha256", "foreign")
    with pytest.raises(ContentPlanError):
        source_bytes(source)
