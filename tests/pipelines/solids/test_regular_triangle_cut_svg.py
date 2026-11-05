"""Projected incidence, exact parent lettering and clear generated diagrams."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from midpoint_source_cases import section
from regular_triangle_cut_source_cases import CASES, GROUPS
from test_pyramid_midsections_lifecycle import without_figures
from test_regular_triangle_cut import condition

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import regular_triangle_cut_svg as drawing
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.distance_sources import source_bytes
from solution_runner.pipelines.triangles.general.angle_label_positions import (
    _intersects,
)
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize(
    "a,e,u", ((8, 16, 4), (12, 24, 6), (8, 20, 3), (8, 12, 3), (8, 15, 5))
)
def test_rendered_points_are_actual_affine_fractions_and_exact_clear_glyphs(a, e, u):
    case = CASES[-1]
    ctx = without_figures(case)
    section(ctx, "condition")["html"] = condition(a, e, u)
    m = selection(ctx)[0]
    handler = get_handler(GROUPS["505417"]["rule"])
    specs = handler.diagram_specs(ctx)
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    meta = drawing.template()
    A, B, C, M = (meta["vertices"][k] for k in ("A", "B", "C", "M"))
    scale = float(root.get("data-projection-scale"))
    assert scale in (1, 1.5, 2, 3)
    origin = A
    A, B, C, M = [
        tuple(origin[i] + scale * (v[i] - origin[i]) for i in (0, 1))
        for v in (A, B, C, M)
    ]
    O = tuple((A[i] + B[i] + C[i]) / 3 for i in (0, 1))
    blend = lambda P, Q, f: tuple(P[i] + f * (Q[i] - P[i]) for i in (0, 1))
    expected = {
        "A": A,
        "B": B,
        "C": C,
        "M": M,
        "O": O,
        "D": blend(A, C, (a - u) / a),
        "E": blend(A, B, (a - u) / a),
        "L": blend(A, M, (e - u) / e),
        "K": blend(A, O, (e - u) / e),
    }
    if m.symbols["section_foot"] == "H":
        expected["H"] = blend(expected["D"], expected["E"], 0.5)
    edges = root.findall(_tag("line"))
    for edge in edges:
        p, q = edge.get("id").split("-")
        assert tuple(
            float(edge.get(k)) for k in ("x1", "y1", "x2", "y2")
        ) == pytest.approx((*expected[p], *expected[q]), abs=1e-5)
        assert edge.get("stroke-width") == "0.75"
    assert not list(root.iter(_tag("image"))) and not list(root.iter(_tag("text")))
    original = ET.fromstring(source_bytes(meta["source"]))
    aux = ET.fromstring(source_bytes(meta["aux_source"]))
    boxes = []
    for name, point in expected.items():
        group = next(g for g in root if g.get("id") == "label-" + name)
        glyph = (
            aux[meta["aux_index"]]
            if name == "H"
            else original[meta["glyph_indices"][name]]
        )
        assert [p.get("d") for p in group.iter(_tag("path"))] == [
            p.get("d") for p in glyph.iter(_tag("path"))
        ]
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([-\d.]+) ([-\d.]+)\)", group.get("transform")
            ).groups(),
        )
        x, y, w, h = meta["aux_box"] if name == "H" else meta["glyph_boxes"][name]
        box = (x + dx, y + dy, w, h)
        assert not any(
            _intersects(
                tuple(float(e.get(k)) for k in ("x1", "y1")),
                tuple(float(e.get(k)) for k in ("x2", "y2")),
                box,
            )
            for e in edges
        )

        assert math.dist(point, (box[0] + w / 2, box[1] + h / 2)) <= 22.000001
        boxes.append(box)
    for i, (x, y, w, h) in enumerate(boxes):
        assert not any(
            x < bx + bw + 1 and x + w + 1 > bx and y < by + bh + 1 and y + h + 1 > by
            for bx, by, bw, bh in boxes[i + 1 :]
        )
    vx, vy, vw, vh = map(float, root.get("viewBox").split())
    assert all(
        vx < x and vy < y and x + w < vx + vw and y + h < vy + vh
        for x, y, w, h in boxes
    )
    assert drawing.render(m) == drawing.render(m)


def test_changed_template_pin_is_refused(monkeypatch):
    m = selection(CASES[-1]["context"])[0]
    monkeypatch.setattr(drawing, "TEMPLATE_SHA256", "0" * 64)
    with pytest.raises(ContentPlanError, match="template changed"):
        drawing.render(m)


def test_old_successful_plain_box_does_not_enter_the_new_reader(monkeypatch):
    from distance_source_cases import CASES as boxes

    from solution_runner.pipelines.solids import regular_triangle_cut_model

    def unexpected(raw):
        raise AssertionError("the successful box path reached the new fallback")

    monkeypatch.setattr(regular_triangle_cut_model, "read", unexpected)
    case = next(c for c in boxes if c["task"] == "285841")
    assert selection(deepcopy(case["context"]))[0].mode == "diagonal"
