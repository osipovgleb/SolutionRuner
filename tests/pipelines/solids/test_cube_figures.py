"""Exact source reuse, solution ownership and actual projected midpoint geometry."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from cube_source_cases import CASES, GROUPS, generated, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids import cube_section_svg as svg
from solution_runner.pipelines.solids.cube_section_model import VERTICES, CubeSection
from solution_runner.pipelines.solids.cube_sources import SOURCES, source_bytes
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_sources_are_exact_and_aliases_share_canonical_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert raw == source_bytes(SOURCES[source][0])
    root = ET.fromstring(raw)
    assert not list(root.iter(_tag("image"))) and not list(root.iter(_tag("text")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_cases_keep_figure_role_and_existing_compatible_identity(case):
    ctx = deepcopy(case["context"])
    m = read(case)
    replay(ctx, plan(case).transformations)
    assets = ctx["normalized_content"]["assets"]
    assert len(assets) == 1
    if m.mode == "midpoint_section_angle":
        key = svg.KEY if not svg.compatible(m) else "image_1"
        assert section(ctx, "condition") == section(case["context"], "condition")
        assert section(ctx, "solution")["asset_keys"] == [key]
        assert (
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
            .find("p")
            .find("img")
        )
        assert assets[0]["asset_id"] == (
            generated(case, case["context"])[0]["source_asset_id"]
            if key == svg.KEY
            else svg.SOURCE
        )
    else:
        assert section(ctx, "condition")["asset_keys"] == ["image_1"]
        assert section(ctx, "solution")["asset_keys"] == []
        before = case["context"]["normalized_content"]["assets"]
        if before:
            assert assets[0]["asset_id"] == before[0]["asset_id"]


@pytest.mark.parametrize("corner", VERTICES)
def test_section_uses_actual_midpoints_and_face_visibility(corner):
    p = VERTICES[corner]
    neighbors = [
        v for v, q in VERTICES.items() if sum(abs(x - y) for x, y in zip(p, q)) == 1
    ]
    m = CubeSection(
        tuple((n, corner, v) for n, v in zip("KLM", neighbors)),
        corner,
        "MLK",
        sp.Integer(60),
    )
    root = ET.fromstring(svg.figure_svg(m))
    positions = svg.midpoint_positions(m)
    assert len([e for e in root if e.get("id", "").startswith("edge-")]) == 12
    for a, b in [("K", "L"), ("L", "M"), ("M", "K")]:
        edge = next(e for e in root if e.get("id") == "section-" + a + b)
        xy = tuple(float(edge.get(k)) for k in ("x1", "y1", "x2", "y2"))
        assert xy == pytest.approx(
            (*svg.project(positions[a]), *svg.project(positions[b])), abs=1e-5
        )
        assert bool(edge.get("stroke-dasharray")) == svg.hidden_face(
            positions[a], positions[b]
        )
        assert sum((x - y) ** 2 for x, y in zip(positions[a], positions[b])) == 0.5
    assert len([e for e in root if e.get("id") == "section-fill"]) == 1


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "owner", "duplicate", "unreferenced"]
)
def test_unreviewed_or_misowned_figures_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    owner = "solution" if group == "315130" else "condition"
    sec = section(ctx, owner)
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find("img")
    if change == "foreign":
        a["asset_id"], a["url"] = "foreign", "/assets/foreign"
        image["data-asset-id"], image["src"] = a["asset_id"], a["url"]
    elif change == "url":
        a["url"] = image["src"] = "/assets/foreign"
    elif change == "duplicate":
        ctx["normalized_content"]["assets"].append(deepcopy(a))
    elif change == "owner":
        other = section(ctx, "condition" if owner == "solution" else "solution")
        other["html"] += str(image)
        other["asset_keys"] = ["image_1"]
        image.decompose()
        sec["asset_keys"] = []
    else:
        image.decompose()
        sec["asset_keys"] = []
    sec["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("change", ["sha256", "asset_key", "url", "source_asset_id"])
def test_generated_geometry_metadata_is_bound_to_the_condition(change):
    case = next(c for c in CASES if c["task"] == "320147")
    items = list(generated(case, case["context"]))
    items[0][change] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(items))
