"""Verify exact reuse, canonical ownership and generated actual polyhedron edges."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from polyhedron_source_cases import CASES, GROUPS, plan, read
from test_distance_figures import vertices_from_svg
from test_polyhedron_preparation import condition, verify_proof

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids.polyhedron_sources import (
    SOLIDS,
    SOURCES,
    STYLES,
    source_bytes,
)
from solution_runner.pipelines.solids.polyhedron_svg import edges, template
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_source_bytes_remain_exact(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert not list(ET.fromstring(raw).iter(_tag("image")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_uses_exact_existing_scenes_in_the_parent_roles(case):
    ctx = deepcopy(case["context"])
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(ctx) == ()
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    m = read({**case, "context": ctx})
    assets = {a["asset_key"]: a for a in ctx["normalized_content"]["assets"]}
    for role, kind, _ in STYLES[handler.key]["roles"]:
        key = "image_1" if role == "condition" else "image_2"
        expected = None if kind == "frame" else m.solid.vertices
        assert SOLIDS[assets[key]["asset_id"]] == expected
        assert section(ctx, role)["asset_keys"] == [key]
    assert set(assets) == (
        {"image_1"} if case["group"] in {"27209", "639664"} else {"image_1", "image_2"}
    )
    if case["task"] in {"264513", "266013"}:
        old = case["context"]["normalized_content"]["assets"][0]
        assert assets["image_2"]["asset_id"] == old["asset_id"]
        rewrites = [
            t
            for t in result.transformations
            if t["transformation_target_id"] == "asset:image_1"
        ]
        assert len(rewrites) == 1 and rewrites[0]["operation"] == "rewrite"
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "names",
    [
        ("A", "B", "D", "C_1"),
        ("A", "B", "C", "D", "D_1"),
        ("A", "B", "D", "A_1", "B_1", "D_1"),
    ],
)
def test_all_parent_templates_generate_real_vertices_edges_glyphs_and_styles(
    group, names
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    old = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    section(ctx, "condition")["html"] = condition(names).replace(
        "<p>", "<p>" + str(old), 1
    )
    handler = get_handler(GROUPS[group]["rule"])
    specs = handler.diagram_specs(ctx)
    m = read({**case, "context": ctx})
    assert len(specs) == 1
    base = next(
        source for _, kind, source in STYLES[handler.key]["roles"] if kind == "solid"
    )
    meta = template(base)
    original = [
        g
        for g in ET.fromstring(source_bytes(base)).findall(_tag("g"))
        if list(g.iter(_tag("path")))
    ]
    root = ET.fromstring(specs[0]["svg_text"])
    vertices = vertices_from_svg(root)
    observed = {}
    for node in root.findall(_tag("line")):
        if not node.get("id", "").startswith("helper-"):
            continue
        a, b = node.get("id").removeprefix("helper-").split("-")
        observed[a, b] = node
        for name, suffix in [(a, "1"), (b, "2")]:
            assert (
                tuple(float(node.get(axis + suffix)) for axis in ("x", "y"))
                == vertices[name]
            )
        style = (
            meta["cube_style"] if len(c.axes(a + b)) == 1 else meta["diagonal_style"]
        )
        assert (
            node.get("stroke") == style["stroke"]
            and node.get("stroke-width") == style["stroke-width"]
        )
    assert set(observed) == set(edges(m.solid))
    for name, index in meta["glyph_indices"].items():
        glyph = root.find(".//*[@id='vertex-" + name + "']")
        assert glyph is not None
        assert [p.get("d") for p in glyph.iter(_tag("path"))] == [
            p.get("d") for p in original[index].iter(_tag("path"))
        ]
    result = plan(case, ctx)
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "unreferenced", "instruction"]
)
def test_unknown_figure_metadata_and_instructions_are_rejected(case, field):
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
                if img.get("data-asset-key") == asset["asset_key"]:
                    img.decompose()
            s["html"] = str(soup)
            s["asset_keys"] = [
                k for k in s.get("asset_keys", []) if k != asset["asset_key"]
            ]
    else:
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("field", ["asset_key", "sha256", "url", "source_asset_id"])
def test_generated_metadata_must_match_the_actual_svg(field):
    case = next(c for c in CASES if c["task"] == "639664")
    ctx = deepcopy(case["context"])
    old = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    section(ctx, "condition")["html"] = condition(("A", "B", "C", "D", "D_1")).replace(
        "<p>", "<p>" + str(old), 1
    )
    handler = get_handler(GROUPS[case["group"]]["rule"])
    s = handler.diagram_specs(ctx)[0]
    generated = {
        "asset_key": s["asset_key"],
        "sha256": s["sha256"],
        "source_asset_id": "preview-known",
        "url": "/assets/preview-known",
    }
    generated[field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=(generated,))
