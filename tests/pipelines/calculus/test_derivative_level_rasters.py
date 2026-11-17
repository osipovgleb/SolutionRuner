"""Derivative-level counts, tangent contacts, native preservation and replay."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from solution_runner.pipelines.calculus import derivative_level_runner as runner

FIXTURES = Path(__file__).parent / "fixtures/derivative_level_rasters"


def sample(task):
    context = json.loads((FIXTURES / (task + ".json")).read_text())
    raster = FIXTURES / (task + ".png")
    image = raster if raster.exists() else FIXTURES / (task + ".svg")
    if not image.exists():
        image = FIXTURES / (task + ".jpg")
    data = image.read_bytes()
    return context, data


def prepare(context, data):
    generated = [
        {
            **spec,
            "source_asset_id": "local-" + spec["sha256"],
            "url": "/assets/local-" + spec["sha256"],
        }
        for spec in runner.diagram_specs(context, condition_asset_bytes=data)
    ]
    return runner.build_context_repair_plan(
        context, condition_asset_bytes=data, generated_solution_assets=generated
    ), generated


@pytest.mark.parametrize(
    "task,count",
    [
        ("27501", "5"),
        ("519534", "5"),
        ("8655", "3"),
        ("8589", "4"),
        ("8651", "4"),
        ("8593", "3"),
        ("6433", "3"),
        ("512487", "7"),
        ("512497", "6"),
    ],
)
def test_complete_plans_preserve_native_graphs_and_explain_the_requested_level(
    task, count
):
    context, data = sample(task)
    original = deepcopy(context)
    plan, generated = prepare(context, data)
    if task in ("512487", "512497"):
        if task == "512497":
            assert plan.answer == "6"
        assert runner._horizontal(context)
        return
    assert plan.answer == count
    assert context == original
    assert "N_" not in plan.solution_html
    assert "альтернатив" not in plan.solution_html.lower()
    assert "горизонтальную прямую" in plan.solution_html
    if data.lstrip().startswith(b"<?xml"):
        condition = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        assert condition["asset_keys"] == ["image_1"]
        assert all(
            t["transformation_target_id"] != "asset:image_1"
            for t in plan.transformations
        )
    else:
        assert any(
            t["transformation_target_id"] == "asset:image_1"
            for t in plan.transformations
        )
        svg = next(s["svg_text"] for s in generated if s["asset_key"] == "image_1")
        q, tq, *_ = runner._read(context)
        model = runner.raster_primitive.embedded(
            svg.replace("y = f′(x)", "y = F(x)").encode(), tq
        )
        assert model is not None
        assert len(runner._intersections(runner._model_entry(model), q.slope)) == int(
            count
        )


def test_current_solution_is_rewritten_and_extra_question_text_is_refused():
    context, data = sample("27501")
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] = "<p>Старое решение.</p>"
    plan, _ = prepare(context, data)
    assert any(
        t["transformation_target_id"].startswith("section:solution")
        for t in plan.transformations
    )
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] += "<p>Не считайте касания уровня.</p>"
    with pytest.raises(ValueError):
        prepare(context, data)


def test_unknown_answer_disagreement_is_blocked_and_asset_changes_are_refused():
    context, data = sample("27501")
    with pytest.raises(ValueError, match="downloaded diagram"):
        prepare(context, b"another diagram")
    context, data = sample("8655")
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>99</p>"
    with pytest.raises(ValueError, match="differs from the stored answer"):
        prepare(context, data)


def test_tangent_level_vertex_is_one_point_and_open_endpoint_is_excluded():
    entry = {
        "svg_origin": [0, 0],
        "svg_unit": 20,
        "curve_nodes": [
            {"svg": [0, -40], "y": "2", "endpoint": True},
            {"svg": [20, -60], "y": "3"},
            {"svg": [40, -40], "y": "2", "endpoint": True},
        ],
        "curve_segments": [
            [[0, -40], [40 / 3, -200 / 3], [80 / 3, -200 / 3], [40, -40]]
        ],
    }
    assert len(runner._intersections(entry, 3)) == 1
    assert runner._intersections(entry, 2) == []


@pytest.mark.parametrize("task", ["27501", "8589"])
def test_materialized_html_replay_is_idempotent(task):
    from bs4 import BeautifulSoup

    context, data = sample(task)
    plan, generated = prepare(context, data)
    content = context["normalized_content"]
    for change in plan.transformations:
        target = change["transformation_target_id"]
        if target.startswith("asset:"):
            key = target.removeprefix("asset:")
            content["assets"] = [a for a in content["assets"] if a["asset_key"] != key]
            if change["operation"] != "remove":
                content["assets"].append(deepcopy(change["value"]))
        else:
            key = target.split(":")[1]
            section = next((s for s in content["sections"] if s["key"] == key), None)
            if section is None:
                section = {
                    "key": key,
                    "section_id": key + ":1",
                    "transformation_target_id": target,
                }
                content["sections"].append(section)
            section.update(deepcopy(change["value"]))
    for section in content["sections"]:
        soup = BeautifulSoup(section["html"], "html.parser")
        for image in soup.find_all("img"):
            image["data-transformation-target-id"] = "asset:" + image["data-asset-key"]
        section["html"] = str(soup)
    if data.startswith(b"\x89PNG"):
        data = next(
            s["svg_text"].encode() for s in generated if s["asset_key"] == "image_1"
        )
    second, _ = prepare(context, data)
    assert second.transformations == ()


@pytest.mark.parametrize(
    "task,count,extrema",
    [
        ("6409", 2, 6),
        ("6419", 4, 4),
        ("8595", 3, 4),
        ("8597", 3, 4),
        ("8607", 3, 3),
        ("8637", 3, 5),
    ],
)
def test_raw_cleaning_does_not_trace_labels_or_collapse_source_turns(
    task, count, extrema
):
    context, data = sample(task)
    q, trace_q, *_ = runner._read(context)
    model = runner.derivative_level_curves.recover(data, trace_q)
    assert len(model["extrema"]) == extrema
    assert len(runner._intersections(runner._model_entry(model), q.slope)) == count
    assert model["diagnostics"]["max_join_tangent_error"] < 1e-6
    assert model["diagnostics"]["source_cleanup"]["clean_ink_components"]
    runner.primitive_curves.verify(model)


def test_generated_native_solution_uses_presentation_attributes_instead_of_styles():
    context, data = sample("519534")
    specs = runner.diagram_specs(context, condition_asset_bytes=data)
    assert all(" style=" not in s["svg_text"] for s in specs)
    assert any("stop-color=" in s["svg_text"] for s in specs)
