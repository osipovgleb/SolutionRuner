"""Horizontal-tangent PNG conversion preserves curves and two-paragraph conditions."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from test_raster_rays import Gateway as BaseGateway

from solution_runner.pipelines.calculus import stationary_raster_runner as runner
from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)

ROOT = Path(__file__).parent / "fixtures/horizontal_rasters"
RULE = "calculus-raster-horizontal-tangents"


class Gateway(BaseGateway):
    def __init__(self, task):
        self.context = json.loads((ROOT / (task + ".json")).read_text())
        asset = self.context["normalized_content"]["assets"][0]
        self.files = {
            asset["asset_id"]: (
                ROOT
                / (task + (".svg" if (ROOT / (task + ".svg")).exists() else ".png"))
            ).read_bytes()
        }
        self.uploads = self.writes = 0


@pytest.mark.parametrize(
    "task,count",
    [
        ("7091", 4),
        ("7093", 8),
        ("7095", 7),
        ("7099", 7),
        ("7101", 7),
        ("27489", 4),
        ("560131", 5),
    ],
)
def test_normal_run_prepare_apply_and_readback(task, count):
    gateway = Gateway(task)
    before = deepcopy(gateway.context)
    record = _prepared_record(gateway, before, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == str(count)
    assert gateway.context == before and gateway.uploads == gateway.writes == 0
    condition = next(
        t["value"]["html"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith("section:condition")
    )
    soup = BeautifulSoup(condition, "html.parser")
    assert len(soup.find_all("p", recursive=False)) == 2
    assert 'data-inline-latex="y=' in str(soup.find_all("p")[1])
    assert len(soup.find_all("img")) == 1
    if task not in ("27489", "560131"):
        assert len(record["generated_diagrams"]) == 2
        raw = record["generated_diagrams"][0]["svg_text"]
        assert "y = f(x)" in raw and "y = F(x)" not in raw
        assert ET.fromstring(raw).tag.endswith("svg")
    outcome = _apply_record(gateway, record, None, RULE)
    assert outcome["status"] == "applied", outcome
    assert (
        _prepared_record(gateway, gateway.context, None, RULE)["transformations"] == []
    )
    if task in ("27489", "560131"):
        old = before["normalized_content"]["assets"][0]
        assert (
            next(
                a
                for a in gateway.context["normalized_content"]["assets"]
                if a["asset_key"] == old["asset_key"]
            )
            == old
        )


def test_source_count_disagreement_needs_review_but_horizontal_level_does_not():
    gateway = Gateway("7091")
    _question, _, _, model, selected = runner._model(
        gateway.context, next(iter(gateway.files.values()))
    )
    assert len(selected) == 4
    changed = deepcopy(gateway.context)
    next(s for s in changed["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>99</p>"
    with pytest.raises(ValueError, match="differs from the stored answer"):
        runner._model(changed, next(iter(gateway.files.values())))
    changed = deepcopy(gateway.context)
    condition = next(
        s for s in changed["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        "y=-3", "y=" + str(round(model["extrema"][0]["y"]))
    )
    *_, selected = runner._model(changed, next(iter(gateway.files.values())))
    assert len(selected) == 4
    html = runner.proof(runner._read(changed)[0], selected)
    assert "Их количество — 4" in html
    assert "N_" not in html
    assert "neq" not in html
    assert "не считаем" not in html


def test_junk_source_answers_are_not_used_as_a_numeric_reference():
    gateway = Gateway("7091")
    answer_section = next(
        s
        for s in gateway.context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    for value in ("000", "+", ".", "а"):
        answer_section["html"] = "<p>" + value + "</p>"
        runner._check_count(gateway.context, 4)
    answer_section["html"] = "<p>0</p>"
    with pytest.raises(ValueError, match="differs from the stored answer"):
        runner._check_count(gateway.context, 4)


def test_blocked_count_still_has_numbered_comparison_but_cannot_be_applied(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(runner, "APPROVED_COUNTS", tmp_path / "unreviewed.json")
    from solution_runner.dashboard.previews import _preview_records, _sample

    gateway = Gateway("7111")
    record = _prepared_record(gateway, gateway.context, None, RULE)
    assert record["status"] == "blocked"
    assert record["transformations"] == [] and "expected_answer" not in record
    review = record["review_preview"]
    assert review["calculated_answer"] == "7" and review["stored_answer"] == "6"
    assert _preview_records({"records": [record]}) == [record]
    sample = _sample(gateway, record)
    assert sample["review_only"] and sample["after"] is not None
    assert "Применение заблокировано" in sample["after"]["solution_html"]
    assert "data:image/svg+xml;base64," in sample["after"]["condition_html"]
    assert "Сохранённый ответ" in sample["after"]["solution_html"]
    svg = ET.fromstring(review["generated_diagrams"][0]["svg_text"])
    ns = "{http://www.w3.org/2000/svg}"
    group = svg.find(ns + 'g[@data-runner-diagram="stationary_points"]')
    assert [n.text for n in group.findall(ns + "text")] == list(map(str, range(1, 8)))
    assert _apply_record(gateway, record, None, RULE)["status"] == "blocked"
    assert gateway.uploads == gateway.writes == 0


@pytest.mark.parametrize("task,count", [("560724", 3), ("560773", 4)])
def test_handwritten_native_derivative_solutions_preserve_the_exact_svg(task, count):
    gateway = Gateway(task)
    before = deepcopy(gateway.context)
    record = _prepared_record(gateway, before, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == str(count)
    assert record["generated_diagrams"] == []
    assert all(
        not t["transformation_target_id"].startswith(("section:condition", "asset:"))
        for t in record["transformations"]
    )
    assert _apply_record(gateway, record, None, RULE)["status"] == "applied"
    assert (
        _prepared_record(gateway, gateway.context, None, RULE)["transformations"] == []
    )
    assert gateway.uploads == 0
    assert (
        gateway.context["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )


def test_user_approved_count_is_bound_to_source_bytes_and_question():
    gateway = Gateway("7111")
    record = _prepared_record(gateway, gateway.context, None, RULE)
    assert record["status"] == "prepared" and record["expected_answer"] == "7", record
    assert _apply_record(gateway, record, None, RULE)["status"] == "applied"
    assert (
        _prepared_record(gateway, gateway.context, None, RULE)["transformations"] == []
    )


@pytest.mark.parametrize(
    "task,count",
    [("7161", 7), ("7121", 6), ("7137", 8), ("7183", 9), ("7201", 4), ("7291", 7)],
)
def test_header_grid_caps_and_steep_troughs_keep_the_real_stationary_points(
    task, count
):
    gateway = Gateway(task)
    _, _, _, model, points = runner._model(
        gateway.context, next(iter(gateway.files.values())), review=True
    )
    assert len(points) == count
    assert model["diagnostics"]["max_trace_error_cells"] < 0.25
    assert model["diagnostics"]["curvature_jump_after"] < 1e-6
    if task == "7161":
        assert model["extrema"][0]["kind"] == "min"
        assert model["extrema"][0]["x"] > -4.2


def test_changed_question_cannot_reuse_an_approved_count():
    gateway = Gateway("7111")
    condition = next(
        s
        for s in gateway.context["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("y=-8", "y=-9")
    record = _prepared_record(gateway, gateway.context, None, RULE)
    assert record["status"] == "blocked"
    assert record["review_preview"]["calculated_answer"] == "7"
    assert record["transformations"] == []


def test_handwritten_solution_refuses_a_changed_graph_or_question():
    from solution_runner.pipelines.calculus import horizontal_manual

    gateway = Gateway("560724")
    data = next(iter(gateway.files.values()))
    with pytest.raises(ValueError, match="current graph"):
        horizontal_manual.build(gateway.context, data + b" ")
    context = deepcopy(gateway.context)
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] += "<p>Кроме точки x_6.</p>"
    with pytest.raises(ValueError, match="full current question"):
        horizontal_manual.build(context, data)


@pytest.mark.parametrize("task,count", [("7135", 7), ("7169", 7), ("7199", 6)])
def test_reviewed_coincidence_wording_is_applied_and_survives_readback(task, count):
    gateway = Gateway(task)
    record = _prepared_record(gateway, gateway.context, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == str(count)
    html = next(
        t["value"]["html"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith("section:condition")
    )
    assert "или совпадает с ней" in html
    assert _apply_record(gateway, record, None, RULE)["status"] == "applied"
    assert (
        _prepared_record(gateway, gateway.context, None, RULE)["transformations"] == []
    )


def test_new_png_bytes_still_use_the_scoped_trace_and_keep_the_corrected_extrema():
    gateway = Gateway("7161")
    # Equivalent PNG with a new digest forces an unseen-image conversion.
    data = next(iter(gateway.files.values())) + b"\n"
    _, _, _, model, points = runner._model(gateway.context, data, review=True)
    assert len(points) == 7 and model["extrema"][0]["kind"] == "min"
    assert model["diagnostics"]["source_cleanup"]["header_mask"][2] > 800
