"""Tangent extraction, signed lattice slopes, preserved SVGs and replay."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from graph_samples import _apply_local

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
        ("704615", "-0,2"),
        ("9209", "1,5"),
        ("525401", "-4"),
        ("665317", "-1,4"),
    ],
)
def test_geometry_gives_signed_slope_without_using_stored_answer(task, answer):
    c, data = sample(task)
    original = deepcopy(c)
    next(s for s in c["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    plan, generated = prepare(c, data)
    assert plan.answer == answer
    assert "треугольник" in plan.solution_html
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
    assert get_group_profile("27504").content_rule_key == "calculus-graph-tangent-slope"
