"""Check section reuse, source identity and actual generated diagonals and letters."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from box_section_source_cases import CASES, GROUPS, generated, plan, read
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from test_box_section_preparation import RECTANGLES, condition
from test_distance_figures import vertices_from_svg

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.box_section_sources import (
    FIGURES,
    PARENTS,
    SOURCES,
    source_bytes,
)
from solution_runner.pipelines.solids.box_section_svg import helpers, template
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_source_bytes_and_unembedded_unnumbered_figures(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    root = ET.fromstring(raw)
    assert not list(root.iter(_tag("image"))) and not list(root.iter(_tag("text")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_compatible_source_ids_reused_exactly_in_solution(case):
    ctx = deepcopy(case["context"])
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(ctx) == ()
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert section(ctx, "condition")["asset_keys"] == []
    moved = case["group"] == "316552" and case["task"] != "316552"
    assert section(ctx, "solution")["asset_keys"] == ["image_2" if moved else "image_1"]
    assert (
        ctx["normalized_content"]["assets"][0]["asset_id"]
        == case["context"]["normalized_content"]["assets"][0]["asset_id"]
    )
    assert FIGURES[ctx["normalized_content"]["assets"][0]["asset_id"]] == tuple(
        sorted(read(case).vertices)
    )
    if case["group"] == "316552" and case["task"] != "316552":
        assert any(
            t["transformation_target_id"] == "asset:image_2" and t["operation"] == "add"
            for t in result.transformations
        )


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("rectangle", RECTANGLES)
def test_all_six_plane_scenes_preserve_actual_vertices_helpers_and_source_glyphs(
    group, rectangle
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(sorted(rectangle)[:3])
    handler = get_handler(GROUPS[group]["rule"])
    specs = handler.diagram_specs(ctx)
    if any(set(rectangle) == set(v) for v in FIGURES.values()):
        assert specs == ()
        return
    assert len(specs) == 1
    m = read({**case, "context": ctx})
    base = PARENTS[GROUPS[group]["rule"]][0]
    meta = template(base)
    root = ET.fromstring(specs[0]["svg_text"])
    vertices = vertices_from_svg(root)
    original = [
        g
        for g in ET.fromstring(source_bytes(base)).findall(_tag("g"))
        if list(g.iter(_tag("path")))
    ]
    observed = set()
    for node in root.findall(_tag("line")):
        if not node.get("id", "").startswith("helper-"):
            continue
        a, b = node.get("id").removeprefix("helper-").split("-")
        observed.add((a, b))
        for name, suffix in [(a, "1"), (b, "2")]:
            assert (
                tuple(float(node.get(axis + suffix)) for axis in ("x", "y"))
                == vertices[name]
            )
        assert node.get("stroke") == "#143B8F" and node.get("stroke-width") == "0.75"
    assert observed == set(helpers(m, base))
    assert (
        len(
            [
                n
                for n in root.findall(_tag("line"))
                if n.get("id", "").startswith("wire-")
            ]
        )
        == 12
    )
    for name, index in meta["glyph_indices"].items():
        glyph = root.find(".//*[@id='vertex-" + name + "']")
        assert [p.get("d") for p in glyph.iter(_tag("path"))] == [
            p.get("d") for p in original[index].iter(_tag("path"))
        ]
    replay(ctx, plan(case, ctx).transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "unreferenced", "instruction"]
)
def test_unreviewed_asset_metadata_and_extra_instructions_rejected(case, field):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    asset = assets[0]
    if field == "foreign":
        asset["asset_id"] = "foreign"
    elif field == "url":
        asset["url"] = "https://example.com/foreign.svg"
    elif field == "duplicate":
        assets.append(deepcopy(asset))
    elif field == "unreferenced":
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                img.decompose()
            s["html"] = str(soup)
            s["asset_keys"] = []
    else:
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("field", ["asset_key", "sha256", "url", "source_asset_id"])
def test_generated_identity_must_match_actual_plane(field):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(("B", "B_1", "D"))
    metadata = list(generated(case, ctx))
    metadata[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=tuple(metadata))
