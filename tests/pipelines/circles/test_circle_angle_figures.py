"""Verify exact source reuse, true numbered arcs and strict asset ownership."""

import hashlib
import math
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from circle_angle_source_cases import CASES, GROUPS, generated, plan, read
from midpoint_source_cases import replay, section
from test_iso_trapezoid_figures import check_labels

from solution_runner.pipelines.circles.angle_figures import KEY, SOURCES
from solution_runner.pipelines.circles.angle_sources import SOURCES as AUDITED
from solution_runner.pipelines.circles.angle_sources import source_bytes
from solution_runner.pipelines.circles.angle_svg import figure_svg
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", sorted(AUDITED))
def test_source_svg_bytes_are_pinned_and_native_circles_are_retained(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == AUDITED[source][1]
    root = ET.fromstring(raw)
    rings = root.findall(_tag("circle")) + [
        path
        for path in root.findall(_tag("path"))
        if path.get("stroke") == "#0D0F0F" and path.get("fill") == "none"
    ]
    assert len(rings) == 1
    if rings[0].tag == _tag("path"):
        assert rings[0].get("d").strip().endswith("z")
    assert not list(root.iter(_tag("image")))
    assert len(root.findall(_tag("line"))) >= 2
    assert source in {s for row in SOURCES.values() for s in row}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_figures_keep_the_correct_section_and_reuse_compatible_ids(case):
    context = deepcopy(case["context"])
    model = read(context)
    handler = get_handler(GROUPS[case["group"]]["rule"])
    drawings = handler.diagram_specs(context)
    assert len(drawings) == (1 if model.mode == "two_arcs" else 0)
    replay(context, plan(case).transformations)
    assets = context["normalized_content"]["assets"]
    assert len(assets) == 1
    condition, solution = section(context, "condition"), section(context, "solution")
    if model.mode == "central_difference":
        assert condition["asset_keys"] == [] and solution["asset_keys"] == ["image_1"]
    else:
        assert condition["asset_keys"] == [KEY if drawings else "image_1"]
        assert solution["asset_keys"] == []
    if not drawings:
        before = case["context"]["normalized_content"]["assets"]
        expected = before[0]["asset_id"] if before else SOURCES[model.mode][0]
        assert (
            assets[0]["asset_id"] == expected
            and assets[0]["url"] == "/assets/" + expected
        )


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "27866"], ids=lambda c: c["task"]
)
def test_numbered_arcs_vertices_and_angle_match_the_exact_task(case):
    model = read(case["context"])
    root = ET.fromstring(figure_svg(model))
    circle = root.find(_tag("circle"))
    center = tuple(float(circle.get(axis)) for axis in ("cx", "cy"))
    radius = float(circle.get("r"))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    xy = lambda e, i: tuple(float(e.get(axis + str(i))) for axis in ("x", "y"))
    p = {
        "A": xy(lines["chord-CA"], 2),
        "C": xy(lines["chord-CA"], 1),
        "B": xy(lines["chord-CB"], 2),
    }
    assert xy(lines["chord-CB"], 1) == p["C"]
    for point in p.values():
        assert math.dist(point, center) == pytest.approx(radius, abs=1e-6)
    angles = {
        n: math.degrees(math.atan2(q[1] - center[1], q[0] - center[0]))
        for n, q in p.items()
    }
    assert (angles["C"] - angles["A"]) % 360 == pytest.approx(
        float(model.given[0]), abs=2e-6
    )
    assert (angles["B"] - angles["C"]) % 360 == pytest.approx(
        float(model.given[1]), abs=2e-6
    )
    u, v = ([p[n][i] - p["C"][i] for i in (0, 1)] for n in "AB")
    angle = math.degrees(
        math.acos(sum(x * y for x, y in zip(u, v)) / math.hypot(*u) / math.hypot(*v))
    )
    assert angle == pytest.approx(float(model.answer), abs=2e-6)
    labels = root.findall(_tag("text"))
    assert [e.text for e in labels] == [str(v) + "°" for v in model.given]
    assert [e.get("id") for e in labels] == ["arc-AC", "arc-BC"]
    segments = [tuple(xy(e, i) for i in (1, 2)) for e in lines.values()]
    check_labels(root, segments)
    x, y, w, h = map(float, root.get("viewBox").split())
    for label in labels:
        lx, ly = float(label.get("x")), float(label.get("y"))
        assert (
            x <= lx
            and ly - 12 >= y
            and lx + 7 * len(label.text) <= x + w
            and ly + 4 <= y + h
        )
        assert label.get("font-family") == "Times New Roman, Times, serif"
    marker = root.find(".//*[@id='angle-ACB']")
    assert marker is not None and marker.get("stroke") == "#143B8F"


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "instruction", "duplicate", "unreferenced", "owner"]
)
def test_foreign_assets_unknown_instructions_and_misownership_fail_closed(
    group, change
):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    asset = context["normalized_content"]["assets"][0]
    owner = next(
        s
        for s in context["normalized_content"]["sections"]
        if asset["asset_key"] in s.get("asset_keys", [])
    )
    soup = BeautifulSoup(owner["html"], "html.parser")
    image = soup.find("img")
    if change == "foreign":
        asset["asset_id"], asset["url"] = "foreign", "/assets/foreign"
        image["data-asset-id"], image["src"] = "foreign", "/assets/foreign"
    elif change == "url":
        asset["url"] = "/assets/other"
    elif change == "duplicate":
        soup.append(deepcopy(image))
    elif change == "unreferenced":
        image.decompose()
        owner["asset_keys"] = []
    elif change == "owner":
        image.extract()
        owner["asset_keys"] = []
        other = (
            section(context, "answer")
            if group == "27866"
            else section(
                context, "condition" if owner["key"] == "solution" else "solution"
            )
        )
        other["html"] = str(image) + other["html"]
        other["asset_keys"] = ["image_1"]
    else:
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
    if change != "instruction" or owner["key"] != "condition":
        owner["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("change", ["key", "sha", "url", "id"])
def test_generated_identity_and_sha_must_match_current_numbered_arcs(change):
    case = next(c for c in CASES if c["task"] == "51343")
    metadata = list(generated(case, case["context"]))
    field = {
        "key": "asset_key",
        "sha": "sha256",
        "url": "url",
        "id": "source_asset_id",
    }[change]
    metadata[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=metadata)
