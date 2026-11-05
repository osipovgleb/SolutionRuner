"""Exact native reuse and actual projected geometry, labels and image ownership."""

import hashlib
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from distance_source_cases import CASES, GROUPS, generated, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import distance_figures, distance_svg
from solution_runner.pipelines.solids.box_coordinates import VERTICES, axes, endpoints
from solution_runner.pipelines.solids.box_distance_geometry import blue
from solution_runner.pipelines.solids.distance_sources import SOURCES, source_bytes
from solution_runner.pipelines.triangles.general.angle_label_positions import (
    _intersects,
)
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_spatial_sources_keep_exact_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert raw == source_bytes(SOURCES[source][0])
    assert not list(ET.fromstring(raw).iter(_tag("image")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_roles_and_correct_generated_figures(case):
    ctx = deepcopy(case["context"])
    model = read(case)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    expected = (
        2
        if case["task"] in {"270573", "270575", "271073", "271075"}
        else 1
        if case["task"] in {"285841", "285843", "285845"}
        else 0
    )
    assert len(specs) == expected
    replay(ctx, plan(case).transformations)
    assets = ctx["normalized_content"]["assets"]
    assert len(assets) == (2 if model.mode in {"distance", "distance_squared"} else 1)
    assert len(section(ctx, "condition")["asset_keys"]) == (
        0 if model.mode == "diagonal" else 1
    )
    assert len(section(ctx, "solution")["asset_keys"]) == (
        0 if model.mode == "edge" else 1
    )
    if model.mode != "edge":
        assert (
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
            .find("p")
            .find("img")
        )
    before = {
        a["asset_key"]: a["asset_id"]
        for a in case["context"]["normalized_content"]["assets"]
    }
    if case["task"] == case["group"] or case["task"] in {"271071", "271571"}:
        assert {a["asset_key"]: a["asset_id"] for a in assets} == before
    if case["task"] in {"916", "917", "918"}:
        assert (
            assets[0]["asset_key"] == "image_1"
            and assets[0]["asset_id"] == before["image_2"]
        )
    for spec in specs:
        assert_svg(spec, model, case["task"])


def vertices_from_svg(root):
    vertices = {}
    for edge in root:
        if not edge.get("id", "").startswith("wire-"):
            continue
        a, b = edge.get("id").removeprefix("wire-").split("-")
        assert len(axes(a + b)) == 1
        for name, suffix in ((a, "1"), (b, "2")):
            point = tuple(float(edge.get(axis + suffix)) for axis in ("x", "y"))
            if name in vertices:
                assert vertices[name] == point
            vertices[name] = point
    assert len(vertices) == 8
    origin = vertices["A"]
    basis = [
        tuple(vertices[n][j] - origin[j] for j in (0, 1)) for n in ("B", "D", "A_1")
    ]
    for name, point in VERTICES.items():
        assert vertices[name] == pytest.approx(
            tuple(
                origin[j] + sum(point[i] * basis[i][j] for i in range(3))
                for j in (0, 1)
            ),
            abs=2e-6,
        )
    return vertices


def label_box(root, meta, name):
    g = next(e for e in root if e.get("id") == "vertex-" + name)
    box = list(meta["glyph_boxes"][name])
    shift = re.fullmatch(r"translate\(([-\d.]+) ([-\d.]+)\)", g.get("transform", ""))
    if shift:
        box[0] += float(shift[1])
        box[1] += float(shift[2])
    return g, box


def assert_svg(spec, model, task):
    root = ET.fromstring(spec["svg_text"])
    role = (
        "condition" if spec["asset_key"] == distance_figures.CONDITION else "solution"
    )
    source = next(
        row[2] for row in distance_figures.ROLES[model.mode] if row[0] == role
    )
    meta = distance_svg.template(source)
    vertices = vertices_from_svg(root)
    helper = [e for e in root if e.get("id", "").startswith("helper-")]
    required, allowed = blue(model, role)
    expected = (
        allowed
        if model.mode == "distance"
        and len(axes(model.requested)) == 2
        and role == "solution"
        else required
    )
    assert len(helper) == len(expected)
    for line in helper:
        a, b = line.get("id").removeprefix("helper-").split("-")
        assert tuple(
            float(line.get(k)) for k in ("x1", "y1", "x2", "y2")
        ) == pytest.approx((*vertices[a], *vertices[b]), abs=1e-5)
        p, q = vertices[a], vertices[b]
        v = (q[0] - p[0], q[1] - p[1])
        square = v[0] ** 2 + v[1] ** 2
        for name, r in vertices.items():
            if name in (a, b):
                continue
            t = ((r[0] - p[0]) * v[0] + (r[1] - p[1]) * v[1]) / square
            if 0 < t < 1:
                assert math.dist(r, (p[0] + t * v[0], p[1] + t * v[1])) >= 4.49999
    original = ET.fromstring(source_bytes(source))
    glyphs = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    x, y, w, h = map(float, root.get("viewBox").split())
    assert all(x < px < x + w and y < py < y + h for px, py in vertices.values())
    for name, index in meta["glyph_indices"].items():
        group, box = label_box(root, meta, name)
        bx, by, bw, bh = box
        assert [p.get("d") for p in group.iter(_tag("path"))] == [
            p.get("d") for p in glyphs[index].iter(_tag("path"))
        ]
        assert x <= bx and y <= by and bx + bw <= x + w and by + bh <= y + h
        for line in root.findall(_tag("line")):
            p = (float(line.get("x1")), float(line.get("y1")))
            q = (float(line.get("x2")), float(line.get("y2")))
            assert not _intersects(p, q, box), (task, name)
    for label in meta["number_labels"]:
        node = next(e for e in root if e.get("id") == "length-" + str(label["axis"]))
        assert node.text == distance_svg.number_text(
            sp.sqrt(model.squares[label["axis"]])
        )


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "owner", "unreferenced", "duplicate", "instruction"]
)
def test_unknown_assets_or_roles_and_unknown_instructions_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    owner = "solution" if group == "284363" else "condition"
    sec = section(ctx, owner)
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find("img")
    if change == "foreign":
        a["asset_id"], a["url"] = "foreign", "/assets/foreign"
        image["data-asset-id"], image["src"] = a["asset_id"], a["url"]
    elif change == "url":
        a["url"] = image["src"] = "/assets/foreign"
    elif change == "owner":
        other = section(ctx, "condition" if owner == "solution" else "solution")
        other["html"] += str(image)
        other["asset_keys"].append(a["asset_key"])
        image.decompose()
        sec["asset_keys"].remove(a["asset_key"])
    elif change == "unreferenced":
        image.decompose()
        sec["asset_keys"].remove(a["asset_key"])
    elif change == "duplicate":
        ctx["normalized_content"]["assets"].append(deepcopy(a))
    else:
        section(ctx, "condition")["html"] += "<p>Округлите ответ.</p>"
        if owner == "condition":
            soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    sec["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("field", ["sha256", "asset_key", "source_asset_id", "url"])
def test_generated_bindings_match_the_exact_new_geometry(field):
    case = next(c for c in CASES if c["task"] == "270573")
    items = list(generated(case, case["context"]))
    items[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(items))


def test_equal_unlabelled_scenes_share_the_same_svg_bytes():
    a = next(c for c in CASES if c["task"] == "285841")
    b = next(c for c in CASES if c["task"] == "285845")
    handler = get_handler(GROUPS[a["group"]]["rule"])
    assert handler.diagram_specs(a["context"]) == handler.diagram_specs(b["context"])


@pytest.mark.parametrize(
    "segment,expected",
    [
        ("AD", True),
        ("BC", False),
        ("AC", True),
        ("A_1C_1", False),
        ("AB_1", False),
        ("DC_1", True),
        ("BD_1", True),
    ],
)
def test_hidden_segments_agree_with_the_three_faces_at_the_back_corner(
    segment, expected
):
    a, b = endpoints(segment)
    assert distance_svg.hidden(a, b, "D") is expected
