"""Actual n-sided geometry, both methods and local frozen diagram lifecycle."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from circumcircle_source_cases import CASES, generated, plan, read
from midpoint_source_cases import replay, section
from test_circumcircle_lifecycle import apply_offline, prepared
from test_iso_trapezoid_figures import check_labels
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.circumcircle_model import read_question
from solution_runner.pipelines.circles.circumcircle_polygon_figures import KEY
from solution_runner.pipelines.circles.circumcircle_polygon_svg import (
    SOURCE,
    figure_svg,
)
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag

POLYGONS = [c for c in CASES if c["group"] == "27930"]
DRAWN = [c for c in POLYGONS if c["task"] != "27930"]


def point(line, index):
    return tuple(float(line.get(axis + str(index))) for axis in ("x", "y"))


@pytest.mark.parametrize("case", DRAWN, ids=lambda c: c["task"])
def test_actual_vertices_chords_angles_and_outlined_labels(case):
    m = read(case["context"])
    root = ET.fromstring(figure_svg(m))
    circle = root.find(_tag("circle"))
    center = tuple(float(circle.get(axis)) for axis in ("cx", "cy"))
    radius = float(circle.get("r"))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    edges = [v for k, v in lines.items() if k.startswith("side-")]
    assert len(edges) == m.answer and len(lines) == m.answer + 2
    vertices = [point(e, 1) for e in edges]
    chord = 2 * radius * math.sin(math.pi / int(m.answer))
    for i, edge in enumerate(edges):
        assert point(edge, 2) == vertices[(i + 1) % len(vertices)]
        assert math.dist(vertices[i], center) == pytest.approx(radius, abs=1e-6)
        assert math.dist(point(edge, 1), point(edge, 2)) == pytest.approx(
            chord, abs=2e-6
        )
        assert edge.get("stroke") == "#0D0F0F" and edge.get("stroke-width") == "0.75"
    a, b = vertices[0], vertices[-1]
    for name, end in [("OA", a), ("OB", b)]:
        ray = lines["radius-" + name]
        assert point(ray, 1) == center and point(ray, 2) == end
        assert ray.get("stroke") == "#143B8F" and ray.get("stroke-width") == "0.75"
    u, v = ([p[i] - a[i] for i in (0, 1)] for p in [vertices[1], b])
    angle = math.degrees(
        math.acos(sum(x * y for x, y in zip(u, v)) / math.hypot(*u) / math.hypot(*v))
    )
    assert angle == pytest.approx(float(m.given[0]), abs=2e-5)
    assert math.degrees(2 * math.asin(math.dist(a, b) / (2 * radius))) == pytest.approx(
        360 / int(m.answer), abs=2e-6
    )
    check_labels(root, [tuple(point(e, i) for i in (1, 2)) for e in lines.values()])
    originals = ET.fromstring(source_bytes(SOURCE)).findall(_tag("g"))
    original_paths = [
        [p.get("d") for p in g.iter(_tag("path"))]
        for g in originals
        if list(g.iter(_tag("path")))
    ]
    groups = root.findall(_tag("g"))
    assert sorted(
        str([p.get("d") for p in g.iter(_tag("path"))]) for g in groups
    ) == sorted(map(str, original_paths))
    assert (
        len(groups) == 4
        and not list(root.iter(_tag("text")))
        and not list(root.iter(_tag("image")))
    )
    for glyph in groups:
        x, y, w, h = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        x, y = x + dx, y + dy
        near = math.hypot(
            max(x - center[0], 0, center[0] - x - w),
            max(y - center[1], 0, center[1] - y - h),
        )
        far = max(math.dist(center, (bx, by)) for bx in (x, x + w) for by in (y, y + h))
        assert far < radius - 0.5 or near > radius + 0.5


@pytest.mark.parametrize("angle", [0, -10, 59, 100, "179.3", 180, 181])
def test_impossible_or_nonintegral_polygons_are_rejected(angle):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>Угол между двумя соседними сторонами правильного многоугольника, вписанного в окружность, равен {angle}°. Найдите число вершин многоугольника.</p>"
        )


def test_unresolvable_svg_precision_rejects_before_allocating_vertices():
    from solution_runner.pipelines.circles.circumcircle_polygon_svg import vertices

    with pytest.raises(ContentPlanError, match="precision"):
        vertices(10**1000)


@pytest.mark.parametrize("change", ["missing", "key", "hash", "id", "url", "duplicate"])
def test_unverified_generated_identity_fails_closed(change):
    case = DRAWN[0]
    assets = list(generated(case, case["context"]))
    if change == "missing":
        assets = []
    elif change == "duplicate":
        assets *= 2
    else:
        key = {
            "key": "asset_key",
            "hash": "sha256",
            "id": "source_asset_id",
            "url": "url",
        }[change]
        assets[0][key] = "" if change == "id" else "wrong"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(assets))


@pytest.mark.parametrize("target", ["asset:" + KEY, "section:solution"])
def test_missing_generated_picture_or_solution_readback_is_failure(target):
    case = DRAWN[0]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(target)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "svg"])
def test_changed_geometry_blocks_before_local_upload_or_write(drift):
    case = DRAWN[0]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if drift == "condition":
        section(gateway.context, "condition")["html"] = section(
            gateway.context, "condition"
        )["html"].replace("168", "160")
    else:
        record["generated_diagrams"][0]["svg_text"] += " "
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes


def test_native_generated_native_transition_keeps_one_picture_and_original_owner():
    case = POLYGONS[0]
    context = deepcopy(case["context"])
    for angle, key in [(168, KEY), (108, "image_1")]:
        section(context, "condition")["html"] = (
            section(context, "condition")["html"]
            .replace("108", "ANGLE")
            .replace("168", "ANGLE")
            .replace("ANGLE", str(angle))
        )
        result = plan(case, context)
        operations = [
            (t["transformation_target_id"], t["operation"])
            for t in result.transformations
        ]
        assert len(operations) == len(set(operations))
        replay(context, result.transformations)
        assert len(context["normalized_content"]["assets"]) == 1
        assert section(context, "solution")["asset_keys"] == [key]
        assert section(context, "condition")["asset_keys"] == []
        assert plan(case, context).transformations == ()
    assert context["normalized_content"]["assets"][0]["asset_id"] == SOURCE
