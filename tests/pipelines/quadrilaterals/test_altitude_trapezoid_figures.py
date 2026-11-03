"""Check both native drawings, real angles, overhangs and height extensions."""

import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from itertools import pairwise

import pytest
from altitude_trapezoid_source_cases import CASES, GROUPS, generated, plan, read
from midpoint_source_cases import section
from test_bisector_figures import point
from test_iso_trapezoid_figures import check_labels
from test_parallelogram_bisectors import geometric_angle

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.quadrilaterals.trapezoid.altitude_model import (
    read_question,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.altitude_svg import (
    PAIRS,
    figure_svg,
)
from solution_runner.pipelines.triangles.right.construction_svg import _tag


def check(model, svg, detailed):
    root = ET.fromstring(svg)
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    p = {a: point(lines["side-" + a + b], 1) for a, b in zip("ABCD", "BCDA")}
    for a, b in ("AB", "BC", "CD", "DA"):
        assert point(lines["side-" + a + b], 2) == p[b]
    scale = math.dist(p["A"], p["D"]) / float(model.large)
    assert math.dist(p["B"], p["C"]) / scale == pytest.approx(
        float(model.small), abs=2e-6
    )
    assert (p["B"][0] - p["A"][0]) / scale == pytest.approx(
        float(model.offset), abs=2e-6
    )
    assert (p["A"][1] - p["B"][1]) / scale == pytest.approx(
        float(model.height), abs=2e-6
    )
    assert geometric_angle(p, "CDA" if model.right else "BAD") == pytest.approx(
        float(model.angle), abs=2e-5
    )
    vertices = [p[n] for n in "ABCD"]
    area = (
        abs(
            sum(
                vertices[i][0] * vertices[(i + 1) % 4][1]
                - vertices[(i + 1) % 4][0] * vertices[i][1]
                for i in range(4)
            )
        )
        / 2
    )
    assert area / scale**2 == pytest.approx(float(model.area), abs=2e-5)
    if model.right:
        assert p["A"][0] == p["B"][0]
    height = [e for name, e in lines.items() if name.startswith("height-")]
    assert len(height) == int(detailed)
    segments = [(point(e, 1), point(e, 2)) for e in lines.values()]
    if detailed:
        h = point(height[0], 2)
        start = point(height[0], 1)
        assert (
            start == p["C" if model.right else "B"]
            and start[0] == h[0]
            and h[1] == p["A"][1]
        )
        assert math.dist(start, h) / scale == pytest.approx(
            float(model.height), abs=2e-6
        )
        assert ("extension-H" in lines) == (
            not model.right and model.offset > model.large
        )
        marker = root.find(_tag("polyline"))
        corners = [
            tuple(map(float, v.split(","))) for v in marker.get("points").split()
        ]
        first = corners[0][0] - corners[1][0], corners[0][1] - corners[1][1]
        last = corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]
        assert abs(sum(first[i] * last[i] for i in (0, 1))) < 1e-5
        assert math.hypot(*first) > 0 and math.hypot(*last) > 0
        segments += list(pairwise(corners))
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    check_labels(root, segments)
    return p


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("part", [0, 1])
def test_all_native_conditions_and_constructions_have_actual_geometry(case, part):
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(case["context"])
    assert len(specs) == 2 and specs == handler.diagram_specs(case["context"])
    check(read(case["context"]), specs[part]["svg_text"], part == 1)


def test_57307_upper_vertex_extends_beyond_d_in_both_diagrams():
    case = next(c for c in CASES if c["task"] == "57307")
    model = read(case["context"])
    for part, source in enumerate(PAIRS[model.mode]):
        p = check(model, figure_svg(model, source), part == 1)
        assert p["C"][0] > p["D"][0] and p["B"][0] < p["D"][0]


@pytest.mark.parametrize(
    "large,side,area,merged", [(2, 10, "7,5", False), (4, 5, "7,5", True)]
)
def test_height_extension_and_coincident_d_h_are_supported(large, side, area, merged):
    model = read_question(
        f"<p>Основания трапеции равны 1 и {large}, боковая сторона равна {side}. Площадь трапеции равна {area}. Найдите острый угол трапеции, прилежащий к данной боковой стороне. Ответ дайте в градусах.</p>"
    )
    for part, source in enumerate(PAIRS[model.mode]):
        svg = figure_svg(model, source)
        check(model, svg, part == 1)
        if part == 1:
            assert ("coincident-D" in svg) == merged


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
@pytest.mark.parametrize("change", ["foreign", "url", "extra", "owner", "instruction"])
def test_unreviewed_sources_and_ownership_block_before_diagram_preparation(
    case, change
):
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if change == "foreign":
        content["assets"][0]["asset_id"] = "foreign"
    elif change == "url":
        content["assets"][0]["url"] += "?foreign"
    elif change == "extra":
        content["assets"].append(deepcopy(content["assets"][0]))
    elif change == "owner":
        section(context, "condition")["asset_keys"] = ["foreign"]
    else:
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context)


@pytest.mark.parametrize("change", ["sha256", "url", "extra", "missing"])
def test_both_generated_diagrams_must_match_the_current_model(change):
    case = CASES[0]
    items = list(generated(case, case["context"]))
    if change == "sha256":
        items[1]["sha256"] = "0" * 64
    elif change == "url":
        items[1]["url"] = "/assets/foreign"
    elif change == "extra":
        items.append(dict(items[0]))
    else:
        items.pop()
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(items))
