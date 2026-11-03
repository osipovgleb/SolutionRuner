"""Parse SVG strokes to check the actual angles, bisectors and unclipped lettering."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bisector_source_cases import CASES, plan
from midpoint_source_cases import section
from test_parallelogram_bisectors import geometric_angle
from test_parallelogram_quantity_model import read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.quadrilaterals.parallelogram.bisector_svg import (
    DOUBLE_SOURCE,
    figure_svg,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_figures import (
    diagram_specs,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_model import (
    read_question,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_sources import (
    source_bytes,
)
from solution_runner.pipelines.triangles.general.angle_label_positions import (
    _intersects,
)
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag

DYNAMIC = [c for c in CASES if c["group"] != "27827"]


def point(line, index):
    return tuple(float(line.get(axis + str(index))) for axis in ("x", "y"))


def check(m, svg):
    root = ET.fromstring(svg)
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    p = {
        name: point(lines["side-" + name + next_name], 1)
        for name, next_name in zip("ABCD", "BCDA")
    }
    for edge in ("AB", "BC", "CD", "DA"):
        assert point(lines["side-" + edge], 2) == p[edge[1]]
    lengths = [math.dist(p[a], p[b]) for a, b in ("AB", "BC", "CD", "DA")]
    assert lengths[0] == pytest.approx(lengths[2], abs=2e-6)
    assert lengths[1] == pytest.approx(lengths[3], abs=2e-6)
    if m.mode == "rhombus_angle":
        assert max(lengths) - min(lengths) < 2e-6
        assert geometric_angle(p, m.known) == pytest.approx(float(m.amount), abs=2e-5)
        assert geometric_angle(p, m.target) == pytest.approx(float(m.answer), abs=2e-5)
        assert {
            k.removeprefix("diagonal-") for k in lines if k.startswith("diagonal-")
        } == set(m.diagonals)
        for diagonal in m.diagonals:
            assert point(lines["diagonal-" + diagonal], 1) == p[diagonal[0]]
            assert point(lines["diagonal-" + diagonal], 2) == p[diagonal[1]]
        assert root.find(_tag("path")).get("id") == "given-angle"
    else:
        p["L"] = point(lines["bisector-BL"], 2)
        assert point(lines["bisector-BL"], 1) == p["B"]
        assert math.dist(p["A"], p["L"]) == pytest.approx(lengths[0], abs=2e-6)
        assert math.dist(p["A"], p["L"]) / math.dist(p["L"], p["D"]) == pytest.approx(
            float(m.given[0] / m.given[1])
        )
        assert geometric_angle(p, "ABL") == pytest.approx(
            geometric_angle(p, "CBL"), abs=2e-5
        )
    _labels_and_canvas(root, lines)
    return p


def _labels_and_canvas(root, lines):
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    segments = [(point(e, 1), point(e, 2)) for e in lines.values()]
    boxes = []
    for glyph in root.findall(_tag("g")):
        if not glyph.get("id", "").startswith("label-"):
            continue
        x, y, w, h = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        box = (x + dx, y + dy, w, h)
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


@pytest.mark.parametrize("case", DYNAMIC, ids=lambda c: c["task"])
def test_all_native_svg_geometry_labels_and_deterministic_output(case):
    m = read(case["context"])
    svg = figure_svg(m)
    assert svg == figure_svg(m)
    check(m, svg)


def test_nearly_flat_four_degree_rhombus_and_both_diagonals_remain_visible():
    case = next(c for c in CASES if c["task"] == "283357")
    p = check(read(case["context"]), figure_svg(read(case["context"])))
    assert 5 < math.dist(p["B"], p["D"]) < 15
    model = read_question(
        "<p>В ромбе ABCD угол CAB равен 30°. Найдите угол BDC. Ответ дайте в градусах.</p>"
    )
    assert model.diagonals == ("AC", "BD")
    check(model, figure_svg(model))


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "27827"], ids=lambda c: c["task"]
)
def test_double_bisector_compatible_source_is_reused_exactly(case):
    assert diagram_specs(case["context"]) == ()
    assert source_bytes(DOUBLE_SOURCE).startswith(b"<?xml")
    result = plan(case)
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
@pytest.mark.parametrize("change", ["foreign", "url", "keys", "extra", "instruction"])
def test_unknown_asset_ownership_and_extra_instructions_block_before_drawing(
    case, change
):
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if change == "foreign":
        content["assets"][0]["asset_id"] = "foreign"
    elif change == "url":
        content["assets"][0]["url"] += "?foreign"
    elif change == "keys":
        owner = next(s for s in content["sections"] if s.get("asset_keys"))
        owner["asset_keys"] = ["foreign"]
    elif change == "extra":
        content["assets"].append(deepcopy(content["assets"][0]))
    else:
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
    with pytest.raises(ContentPlanError):
        diagram_specs(context)


@pytest.mark.parametrize("change", ["sha256", "url", "extra"])
def test_generated_metadata_must_match_the_selected_current_geometry(change):
    case = next(c for c in CASES if c["task"] == "283357")
    from bisector_source_cases import generated

    items = list(generated(case, case["context"]))
    if change == "sha256":
        items[0]["sha256"] = "0" * 64
    elif change == "url":
        items[0]["url"] = "/assets/foreign"
    else:
        items.append(dict(items[0]))
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(items))
