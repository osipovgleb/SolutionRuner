"""Marked-point source samples, source integrity and tangent ambiguity."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import curve_levels
from solution_runner.pipelines.calculus import graph_marked_points as graph
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_marked.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_group_registration_uses_one_shared_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == group["rule"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_are_computed_without_mutation_and_plans_are_idempotent(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    first = plan(case, context)
    assert parse_rational(first.answer) == parse_rational(
        BeautifulSoup(expected, "html.parser").get_text()
    )
    assert context == original
    assert all(
        t["transformation_target_id"].startswith(
            ("section:answer", "section:solution", "asset:")
        )
        for t in first.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>123456</p>"
    assert plan(case, context).answer == first.answer
    context = deepcopy(original)
    _apply_local(context, first.transformations)
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_additional_conditions_and_changed_downloads_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Точки с положительными ординатами не учитывайте.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"changed curve")


@pytest.mark.parametrize(
    "text",
    [
        "x_{1},x_{3}",
        "x_{1},x_{2},...,x_{2}",
        "x_{1},...,x_{4}",
        "x_{1},x_{2},...,x_{8},x_{9}",
        "x_{1},x_{1}",
        "x_{1},x_{2},...,...,x_{8}",
    ],
)
def test_only_complete_consecutive_marker_lists_are_supported(text):
    with pytest.raises(ValueError):
        graph.labels(text)


def test_function_values_are_not_mistaken_for_derivative_signs():
    data, question, points, selected = graph._input(sample("317539")["context"])
    assert all(p["svg"][1] < data[5]["svg_origin"][1] for p in points)
    assert [p["label"] for p in selected] == [1, 2, 5, 6, 7]
    assert question.operation == "strict" and not question.derivative


def test_derivative_sign_is_its_ordinate_and_not_the_slope_of_its_graph():
    data, question, points, selected = graph._input(sample("317541")["context"])
    assert [p["label"] for p in selected] == [4, 5, 6]
    assert points[0]["slopes"][0] > 0
    assert graph.point_sign(points[0], data[5], question.derivative) == -1
    assert points[4]["slopes"][1] < 0
    assert graph.point_sign(points[4], data[5], question.derivative) == 1


def test_horizontal_tangents_are_excluded_from_strict_negative_derivative_count():
    data, question, points, selected = graph._input(sample("500248")["context"])
    assert [p["label"] for p in selected] == [4, 5, 9]
    assert [p["label"] for p in points if graph.point_sign(p, data[5], False) == 0] == [
        3,
        6,
    ]
    monotonic = replace(question, operation="monotonic")
    assert [p["label"] for p in graph.select(monotonic, data[5], points)] == [
        3,
        4,
        5,
        6,
        9,
    ]


def test_wrong_marker_count_or_different_curve_role_cannot_reuse_evidence():
    case = sample("317541")
    for before, after in [("восемь", "девять"), ("производной", "первообразной")]:
        context = deepcopy(case["context"])
        condition = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        condition["html"] = (
            condition["html"].replace("\u00ad", "").replace(before, after)
        )
        with pytest.raises(ValueError):
            plan(case, context)


def test_changed_marker_position_or_falsely_declared_stationary_point_is_refused():
    data, _, _, _ = graph._input(sample("500248")["context"])
    entry = deepcopy(data[5])
    entry["markers"][0]["svg"][1] += 5
    with pytest.raises(ValueError, match="moved"):
        graph.readings(entry)
    entry = deepcopy(data[5])
    entry["markers"][0]["stationary"] = True
    with pytest.raises(ValueError, match="horizontal tangent"):
        graph.readings(entry)
    entry = deepcopy(data[5])
    entry["markers"][2]["adjacent_signs"] = [-1, 1]
    with pytest.raises(ValueError, match="adjacent monotonicity"):
        graph.readings(entry)


def test_ambiguous_comparison_has_no_fallback_to_the_source_answer():
    data, question, points, _ = graph._input(sample("318139")["context"])
    for point in points:
        point["slopes"] = (-1, 1)
    with pytest.raises(ValueError, match="unique comparison"):
        graph.select(question, data[5], points)
    with pytest.raises(ValueError, match="near-horizontal"):
        graph.point_sign(points[0], data[5], False)


def test_changed_comparison_is_computed_and_gets_a_different_local_diagram():
    case = sample("318139")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        condition["html"].replace("\u00ad", "").replace("наименьшее", "наибольшее")
    )
    result = plan(case, context)
    assert result.answer == "3"
    assert (
        graph.diagram_specs(context)[0]["sha256"]
        != graph.diagram_specs(case["context"])[0]["sha256"]
    )
    with pytest.raises(ValueError, match="prepared figure"):
        plan(case, context, generated=())


@pytest.mark.parametrize("task", ["317544", "317543", "525062", "525090", "500248"])
def test_compatible_source_figures_are_reused_exactly(task):
    case = sample(task)
    assert graph.diagram_specs(case["context"]) == ()
    result = plan(case, case["context"])
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    solution = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    if task == "500248":
        assert "выделенных синим" in solution and "выделенных зелёным" in solution
        assert "x_{1};x_{2};x_{7};x_{8}" in solution
    assert (
        BeautifulSoup(solution, "html.parser").img["data-asset-id"]
        == case["context"]["normalized_content"]["assets"][1]["asset_id"]
    )


@pytest.mark.parametrize("task", ["318045", "318055", "318139", "318039"])
def test_local_tangent_illustrations_preserve_curve_axes_labels_and_dot_positions(task):
    data, _, points, _ = graph._input(sample(task)["context"])
    spec = graph.diagram_specs(sample(task)["context"])[0]
    source = ET.fromstring(data[6])
    rendered = ET.fromstring(spec["svg_text"])
    assert source.get("viewBox") == rendered.get("viewBox")
    assert [p.get("d") for p in source.findall(".//{*}path")] == [
        p.get("d") for p in rendered.findall(".//{*}path")
    ]
    group = rendered.find("{*}g[@data-runner-diagram='tangent_comparison']")
    assert 1 <= len(group) <= len(points)
    assert all(node.get("stroke") == "#218BCC" for node in group)
    assert all(
        node.get("font-family") == "Times New Roman,serif"
        for node in rendered.findall(".//{*}text")
        if (node.text or "").strip() == "−"
    )
    assert len(source.findall(".//{*}path")) > 10
    for tangent in group:
        x1, y1, x2, y2 = [float(tangent.get(k)) for k in ["x1", "y1", "x2", "y2"]]
        assert any(
            abs((x2 - x1) * (p["svg"][1] - y1) - (y2 - y1) * (p["svg"][0] - x1)) < 0.001
            for p in points
        )


def test_cubic_marker_reader_handles_joint_samples_and_refuses_vertical_or_missing_branches():
    entry = {"curve_segments": [[[0, 0], [1, 0], [2, 3], [3, 3]]]}
    readings = curve_levels.at_abscissa(entry, 1.5)
    assert readings == [(1.5, -1.5)]
    with pytest.raises(ValueError, match="single graph branch"):
        curve_levels.at_abscissa(entry, 4)
    with pytest.raises(ValueError, match="vertical curve"):
        curve_levels.at_abscissa(
            {"curve_segments": [[[1, 0], [1, 1], [1, 2], [1, 3]]]}, 1
        )
