"""Tangent extraction, signed lattice slopes, preserved SVGs and replay."""

import json
import re
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from graph_samples import _apply_local
from scipy.signal import find_peaks

from solution_runner.pipelines.calculus import primitive_svg
from solution_runner.pipelines.calculus import tangent_slope_runner as runner
from solution_runner.pipelines.core.group_profiles import get_group_profile

FIXTURES = Path(__file__).parent / "fixtures/tangent_slope_rasters"


def sample(task):
    c = json.loads((FIXTURES / (task + ".json")).read_text())
    f = FIXTURES / (task + ".png")
    return c, (f if f.exists() else FIXTURES / (task + ".svg")).read_bytes()


def prepare(c, data):
    specs = runner.diagram_specs(c, condition_asset_bytes=data)
    generated = [
        {
            **s,
            "source_asset_id": "local-" + s["sha256"],
            "url": "/assets/local-" + s["sha256"],
        }
        for s in specs
    ]
    return runner.build_context_repair_plan(
        c, condition_asset_bytes=data, generated_solution_assets=generated
    ), generated


@pytest.mark.parametrize(
    "task,answer",
    [
        ("9531", "2"),
        ("9127", "-1,75"),
        ("679791", "-1,5"),
        ("9057", "-0,25"),
        ("9635", "-0,25"),
        ("672865", "0,5"),
        ("520489", "-1,25"),
        ("549322", "-1,75"),
        ("9545", "0,25"),
        ("9605", "0,25"),
        ("704615", "-0,2"),
        ("9209", "1,5"),
        ("525401", "-4"),
        ("665317", "-1,4"),
    ],
)
def test_geometry_gives_signed_slope_without_using_stored_answer(task, answer):
    c, data = sample(task)
    original = deepcopy(c)
    saved_answer = next(
        (s for s in c["normalized_content"]["sections"] if s["key"] == "answer"), None
    )
    if saved_answer is not None:
        saved_answer["html"] = "<p>999</p>"
    plan, generated = prepare(c, data)
    assert plan.answer == answer
    assert "треугольник" in plan.solution_html
    assert not re.search(r"-\([0-9]", plan.solution_html)
    assert r"\operatorname{tg}" in plan.solution_html
    assert len([s for s in generated if s["asset_key"] == "image_1"]) == int(
        data.startswith(b"\x89PNG")
    )
    assert all(
        not ET.fromstring(s["svg_text"]).findall(".//*[@style]") for s in generated
    )
    if not data.startswith(b"\x89PNG"):
        assert all(
            t["transformation_target_id"] != "asset:image_1"
            for t in plan.transformations
        )
        assert runner.recover(data)[0].encode() == data
    assert original["normalized_content"]["assets"] == c["normalized_content"]["assets"]
    # Materialize through the same section/asset representation as the server.
    changes = plan.transformations
    for t in changes:
        if (
            t["transformation_target_id"] == "asset:image_1"
            and t["operation"] == "rewrite"
        ):
            c["normalized_content"]["assets"] = [
                a
                for a in c["normalized_content"]["assets"]
                if a["asset_key"] != "image_1"
            ]
    _apply_local(c, changes)
    converted = next(
        (s["svg_text"].encode() for s in generated if s["asset_key"] == "image_1"), data
    )
    again, _ = prepare(c, converted)
    assert again.transformations == ()


def test_converted_geometry_is_checksum_bound():
    c, data = sample("9531")
    _, generated = prepare(c, data)
    svg = next(s["svg_text"] for s in generated if s["asset_key"] == "image_1")
    with pytest.raises(ValueError, match="changed after preparation"):
        runner.recover(svg.replace("#143B8F", "#ff0000").encode())


def test_complete_question_and_scope():
    c, data = sample("9531")
    next(s for s in c["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Найдите также минимум.</p>"
    with pytest.raises(ValueError, match="complete tangent slope"):
        prepare(c, data)
    assert (
        get_group_profile("27503").content_rule_key == "calculus-raster-tangent-slope"
    )
    assert (
        get_group_profile("510384").content_rule_key == "calculus-graph-tangent-slope"
    )


def test_minimum_in_partial_bottom_cell_is_visible_in_svg():
    data = (FIXTURES / "9125.png").read_bytes()
    svg, _, _ = runner.recover(data)
    root = ET.fromstring(svg)
    curve = next(
        n
        for n in root.iter()
        if n.tag.endswith("path") and n.get("stroke") == "#143B8F"
    )
    bottom = max(
        float(primitive_svg._at(segment, i / 100)[1])
        for segment in primitive_svg._segments(curve.get("d"))
        for i in range(101)
    )
    assert float(root.get("height")) - 30 < bottom < float(root.get("height"))


def test_axis_digit_does_not_add_a_false_turn_to_the_curve():
    svg, _, _ = runner.recover((FIXTURES / "9147.png").read_bytes())
    root = ET.fromstring(svg)
    curve = next(
        n
        for n in root.iter()
        if n.tag.endswith("path") and n.get("stroke") == "#143B8F"
    )
    ys = [
        float(primitive_svg._at(segment, i / 100)[1])
        for segment in primitive_svg._segments(curve.get("d"))
        for i in range(100)
    ]
    assert len(find_peaks(ys, prominence=1)[0]) == 0
    assert len(find_peaks([-y for y in ys], prominence=1)[0]) == 1
