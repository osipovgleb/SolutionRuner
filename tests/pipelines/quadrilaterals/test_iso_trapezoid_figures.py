"""Check actual SVG lengths, isosceles geometry, height markers and ownership."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from itertools import pairwise

import pytest
from bs4 import BeautifulSoup
from iso_trapezoid_source_cases import CASES, GROUPS, generated, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.quadrilaterals.trapezoid.isosceles_sources import (
    source_bytes,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.isosceles_svg import (
    CE,
    MARKED,
    PLAIN,
    figure_svg,
)
from solution_runner.pipelines.triangles.general.angle_label_positions import (
    _intersects,
)
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag


def point(line, index):
    return tuple(float(line.get(axis + str(index))) for axis in ("x", "y"))


def check_labels(root, segments):
    boxes = []
    for glyph in root.findall(_tag("g")):
        x, y, w, h = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        box = x + dx, y + dy, w, h
        assert not any(_intersects(a, b, box) for a, b in segments)
        assert not any(
            box[0] < bx + bw
            and box[0] + w > bx
            and box[1] < by + bh
            and box[1] + h > by
            for bx, by, bw, bh in boxes
        )
        boxes.append(box)
    x, y, w, h = map(float, root.get("viewBox").split())
    assert all(
        x <= bx and y <= by and bx + bw <= x + w + 1e-5 and by + bh <= y + h + 1e-5
        for bx, by, bw, bh in boxes
    )


def check(m, svg):
    root = ET.fromstring(svg)
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    points = {a: point(lines["side-" + a + b], 1) for a, b in zip("ABCD", "BCDA")}
    for a, b in ("AB", "BC", "CD", "DA"):
        assert point(lines["side-" + a + b], 2) == points[b]
    scale = math.dist(points["A"], points["D"]) / float(m.large)
    assert math.dist(points["B"], points["C"]) / scale == pytest.approx(
        float(m.small), abs=2e-6
    )
    assert math.dist(points["A"], points["B"]) / scale == pytest.approx(
        float(m.leg), abs=2e-6
    )
    assert math.dist(points["C"], points["D"]) / scale == pytest.approx(
        float(m.leg), abs=2e-6
    )
    height = next(e for key, e in lines.items() if key.startswith("height-"))
    a, b = point(height, 1), point(height, 2)
    assert a[0] == b[0] and b[1] == points["A"][1]
    assert math.dist(a, b) / scale == pytest.approx(float(m.height), abs=2e-6)
    q = math.dist(b, points["D"] if height.get("id") == "height-CE" else points["A"])
    assert q / scale == pytest.approx(float(m.projection), abs=2e-6)
    assert math.dist(a, b) / math.dist(points["A"], points["B"]) == pytest.approx(
        float(m.sine)
    )
    markers = root.findall(_tag("polyline"))
    assert len(markers) == 1
    corners = [
        tuple(map(float, p.split(","))) for p in markers[0].get("points").split()
    ]
    u = corners[0][0] - corners[1][0], corners[0][1] - corners[1][1]
    v = corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]
    assert abs(sum(u[i] * v[i] for i in (0, 1))) < 1e-5
    assert math.hypot(*u) > 0 and math.hypot(*v) > 0
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    segments = [(point(e, 1), point(e, 2)) for e in lines.values()] + list(
        pairwise(corners)
    )
    check_labels(root, segments)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_actual_altitudes_scales_labels_and_determinism(case):
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(case["context"])
    assert len(specs) == 1 and specs == handler.diagram_specs(case["context"])
    check(read(case["context"]), specs[0]["svg_text"])


@pytest.mark.parametrize(
    "first,second",
    [
        (
            "c37ee594-116d-4c12-ab84-5fb6f074d03c",
            "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        ),
        (
            "157aa0f8-ea5d-419c-b075-9864f88d2a85",
            "a7aa0827-7b1f-4364-8469-437dfe2fe497",
        ),
    ],
)
def test_native_aliases_are_byte_exact_and_need_no_duplicate_svg(first, second):
    assert source_bytes(first) == source_bytes(second)


@pytest.mark.parametrize("task", ["519802", "519821"])
def test_mixed_ce_condition_and_solution_roles_are_preserved_without_duplicates(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    old = deepcopy(ctx["normalized_content"]["assets"][0])
    replay(ctx, plan(case, ctx).transformations)
    assert len(ctx["normalized_content"]["assets"]) == 2
    assert (
        next(
            a
            for a in ctx["normalized_content"]["assets"]
            if a["asset_key"] == "image_1"
        )
        == old
    )
    assert section(ctx, "condition")["asset_keys"] == ["image_1"]
    assert len(section(ctx, "solution")["asset_keys"]) == 1
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
@pytest.mark.parametrize("change", ["foreign", "url", "extra", "orphan", "instruction"])
def test_unreviewed_assets_ownership_or_instructions_fail_before_drawing(case, change):
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if change == "foreign":
        content["assets"][0]["asset_id"] = "foreign"
    elif change == "url":
        content["assets"][0]["url"] += "?foreign"
    elif change == "extra":
        content["assets"].append(deepcopy(content["assets"][0]))
    elif change == "orphan":
        owner = next(s for s in content["sections"] if s.get("asset_keys"))
        soup = BeautifulSoup(owner["html"], "html.parser")
        soup.find("img").decompose()
        owner["html"] = str(soup)
    else:
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context)


@pytest.mark.parametrize("change", ["sha256", "url", "extra", "missing"])
def test_generated_metadata_must_match_the_current_altitude(change):
    case = CASES[0]
    items = list(generated(case, case["context"]))
    if change == "sha256":
        items[0]["sha256"] = "0" * 64
    elif change == "url":
        items[0]["url"] = "/assets/foreign"
    elif change == "extra":
        items.append(dict(items[0]))
    else:
        items = []
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(items))


@pytest.mark.parametrize("source", [CE, MARKED, PLAIN])
def test_source_markers_and_colors_survive_actual_geometry(source):
    case = next(
        c
        for c in CASES
        if c["task"]
        == ("27439" if source == CE else "27635" if source == MARKED else "27837")
    )
    root = ET.fromstring(figure_svg(read(case["context"]), source))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    height = next(e for key, e in lines.items() if key.startswith("height-"))
    assert height.get("stroke") == ("#007EA5" if source == MARKED else "#143B8F")
    assert sum(key.startswith("equal-") for key in lines) == (
        2 if source == MARKED else 0
    )
