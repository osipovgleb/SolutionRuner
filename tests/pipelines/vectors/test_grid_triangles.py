"""The two triangle methods agree, and coordinate axes keep the audited geometry."""

import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction as F

import pytest
import sympy as sp
from test_coordinate_source_samples import CASES, plan

from solution_runner.pipelines.vectors.grid_triangles import (
    _input,
    diagram_specs,
    geometric_proof,
    render_svg,
    required_assets,
)


@pytest.mark.parametrize(
    "a,b", [(F(3), F(4)), (F(1, 2), F(7, 3)), (F(10), F(-2)), (F(-3), F(4))]
)
def test_geometry_matches_dot_product_for_different_right_triangles(a, b):
    vectors = {"AB": (a, b), "AC": (a, F(0))}
    value, html = geometric_proof(vectors)
    assert value == sp.Rational((a * a).numerator, (a * a).denominator)
    assert "Первый способ" in html and "обратной теореме Пифагора" in html


@pytest.mark.parametrize(
    "vectors",
    [
        {"AB": (F(3), F(4)), "AC": (F(2), F(1))},
        {"AB": (F(1), F(1)), "AC": (F(0), F(0))},
        {"AB": (F(3), F(0)), "AC": (F(3), F(0))},
    ],
)
def test_a_wrong_or_degenerate_right_angle_cannot_use_the_source_proof(vectors):
    with pytest.raises(ValueError, match="nondegenerate right angle"):
        geometric_proof(vectors)


@pytest.mark.parametrize("task", ["654451", "654463"])
def test_transcribed_triangle_vertices_match_the_original_svg_segments(task):
    case = next(c for c in CASES if c["task"] == task)
    *_, entry, source, _vectors = _input(case["context"])
    origin = entry["svg_origin"]
    unit = entry["svg_unit"]
    expected = list(entry["vertices"].values())
    root = ET.fromstring(source)
    lines = [
        t
        for t in root.iter()
        if t.tag.endswith("line") and t.attrib.get("stroke") == "#143B8F"
    ]
    assert len(lines) == 3
    for line in lines:
        for index in ("1", "2"):
            x = (float(line.attrib["x" + index]) - origin[0]) / unit
            y = (origin[1] - float(line.attrib["y" + index])) / unit
            assert any(
                abs(x - p[0]) < 0.003 and abs(y - p[1]) < 0.003 for p in expected
            )


def test_added_axes_leave_every_original_triangle_segment_unchanged():
    case = next(c for c in CASES if c["task"] == "654463")
    original = deepcopy(case["context"])
    *_, entry, source, _vectors = _input(original)
    rendered = render_svg(entry, source)
    blue = lambda root: [
        t.attrib
        for t in root.iter()
        if t.tag.endswith("line") and t.attrib.get("stroke") == "#143B8F"
    ]
    assert blue(ET.fromstring(rendered)) == blue(ET.fromstring(source))
    assert rendered == render_svg(entry, source)
    assert original == case["context"]


def test_parent_reuses_the_existing_coordinate_figure_and_child_prepares_one_svg():
    parent = next(c for c in CASES if c["task"] == "654451")
    child = next(c for c in CASES if c["task"] == "654463")
    assert diagram_specs(parent["context"]) == ()
    assert (
        required_assets(parent["context"])[0]["source_asset_id"]
        == "94194ebf-e02b-4659-9eca-34046d101006"
    )
    assert required_assets(child["context"]) == ()
    specs = diagram_specs(child["context"])
    assert len(specs) == 1
    result = plan(child, deepcopy(child["context"]))
    assert result.answer == "10"
    change = next(
        t
        for t in result.transformations
        if t["transformation_target_id"] == "section:solution:1"
    )
    html = change["value"]["html"]
    assert (
        html.index("Первый способ") < html.index("Второй способ") < html.index("<img")
    )
    assert len(change["value"]["asset_keys"]) == 1
