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
            ("section:answer", "section:solution", "section:condition", "asset:")
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


def test_catalog_style_handles_native_function_images(monkeypatch):
    case = sample("317539")
    data, _, _, _ = graph._input(case["context"])
    condition_key = data[1]["asset_keys"][0]
    asset = next(a for a in data[0]["assets"] if a["asset_key"] == condition_key)
    monkeypatch.setitem(
        graph.graph_input.EVIDENCE,
        asset["asset_id"],
        {**data[5], "catalog_function_style": True},
    )

    (spec,) = graph.diagram_specs(case["context"])
    assert spec["asset_key"] == "marked_function_growth_and_decline"
    figure = ET.fromstring(spec["svg_text"])
    curve = figure.find("{*}g[@data-runner-diagram='monotonic_function_curve']")
    assert {part.get("stroke") for part in curve} == {"#15803d", "#b42318"}
    assert all("C" in part.get("d", "") for part in curve)
    assert figure.findall(".//*[@stroke-dasharray]")
    assert figure.get("width") == "370"
    result = plan(case, case["context"])
    assert result.answer == "5"


def test_derivative_sign_is_its_ordinate_and_not_the_slope_of_its_graph():
    data, question, points, selected = graph._input(sample("317541")["context"])
    assert [p["label"] for p in selected] == [4, 5, 6]
    assert points[0]["slopes"][0] > 0
    assert graph.point_sign(points[0], data[5], question.derivative) == -1
    assert points[4]["slopes"][1] < 0
    assert graph.point_sign(points[4], data[5], question.derivative) == 1


def test_derivative_figure_explains_signs_and_distinguishes_all_markers():
    case = sample("317541")
    (spec,) = graph.diagram_specs(case["context"])
    svg = ET.fromstring(spec["svg_text"])
    chart = svg.find("{*}g[@id='derivative-signs-and-integers']")
    assert [node.text for node in chart.findall("{*}text")] == ["−", "+", "−", "+"]
    assert len(chart.findall("{*}line")) == 3
    assert len(chart.findall("{*}path")) == 8
    markers = svg.find("{*}g[@data-runner-diagram='selected_markers']")
    colors = [node.get("fill") for node in markers.findall("{*}circle")]
    assert colors.count("#15803d") == 3
    assert colors.count("#b42318") == 5
    proof = BeautifulSoup(plan(case, case["context"]).solution_html, "html.parser")
    assert proof.find(True).get_text().startswith("Правило:")
    assert (
        proof.find("img").parent.find_previous_sibling("p").find("b").text == "Правило:"
    )
    assert "На рисунке дана производная" not in proof.get_text()
    assert proof.find_all("p")[-1].find("b").text == "Примечание."


def test_strict_negative_count_displays_classification_only_on_the_graph():
    case = sample("500248")
    spec = graph.diagram_specs(case["context"])[0]
    svg = ET.fromstring(spec["svg_text"])
    markers = svg.find("{*}g[@data-runner-diagram='selected_markers']")
    colors = [node.get("fill") for node in markers.findall("{*}circle")]
    assert colors == [
        "#218BCC" if index in (4, 5, 9) else "#15803d" if index in (3, 6) else "#b42318"
        for index in range(1, 10)
    ]
    chart = svg.find("{*}g[@id='derivative-signs-and-integers']")
    assert [node.text for node in chart.findall("{*}text")] == ["+", "−", "+", "−"]
    proof = BeautifulSoup(plan(case, case["context"]).solution_html, "html.parser")
    assert (
        proof.find("img").parent.find_previous_sibling("p").find("b").text == "Правило:"
    )
    assert [tag.get_text(strip=True) for tag in proof.find_all("p", recursive=False)][
        1:-1
    ] == [
        "В синих точках функция убывает, зелёные точки показывают экстремумы, в красных точках функция возрастает.",
    ]
    assert proof.select_one('[data-inline-latex="N=3"]') is not None


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


def test_changed_comparison_changes_answer_but_keeps_the_tangent_figure():
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
        == graph.diagram_specs(case["context"])[0]["sha256"]
    )
    with pytest.raises(ValueError, match="prepared figure"):
        plan(case, context, generated=())


@pytest.mark.parametrize("task", ["317544", "317543", "525062", "525090"])
def test_all_tangents_replace_legacy_solution_illustrations(task):
    case = sample(task)
    spec = graph.diagram_specs(case["context"])[0]
    assert spec["asset_key"] == "uniform_marked_tangents"
    result = plan(case, case["context"])
    assert any(
        t["transformation_target_id"].startswith("asset:")
        and t["operation"] == "remove"
        for t in result.transformations
    )
    solution = BeautifulSoup(result.solution_html, "html.parser")
    assert solution.img["data-asset-key"] == spec["asset_key"]
    paragraphs = [p.get_text() for p in solution.find_all("p", recursive=False)]
    assert paragraphs[0].startswith("Касательные убывают")
    assert paragraphs[1].startswith("Касательные возрастают")
    assert (
        "У более крутой касательной численное значение больше, например:"
        in paragraphs[2]
    )
    assert paragraphs[-1].startswith("Поэтому выбираем")
    assert "Примечание" not in solution.get_text()
    equalities = [
        row["data-inline-latex"]
        for row in solution.select("center [data-inline-latex]")
    ]
    estimates = {
        formula.split("=")[0]: int(formula.split("=")[1]) for formula in equalities
    }
    _, question, _, _ = graph._input(case["context"])
    maximum = question.target == "наибольшее"
    assert len(estimates) >= 2
    assert all(value > 0 if maximum else value < 0 for value in estimates.values())
    choose = max if maximum else min
    assert estimates[f"f'({result.answer})"] == choose(estimates.values())


@pytest.mark.parametrize("task", ["318045", "318055", "318139", "318039"])
def test_local_tangent_illustrations_preserve_curve_axes_labels_and_dot_positions(task):
    data, _, points, _ = graph._input(sample(task)["context"])
    spec = graph.diagram_specs(sample(task)["context"])[0]
    source = ET.fromstring(data[6])
    rendered = ET.fromstring(spec["svg_text"])
    assert source.get("viewBox") == rendered.get("viewBox")
    assert rendered.get("width") == "370"
    assert [p.get("d") for p in source.findall(".//{*}path")] == [
        p.get("d") for p in rendered.findall(".//{*}path")
    ]
    group = rendered.find("{*}g[@data-runner-diagram='tangent_comparison']")
    tangents = group.findall("{*}line")
    contacts = group.findall("{*}circle")
    assert len(tangents) == len(contacts) == len(points)
    assert list(group) == tangents + contacts
    assert len({float(t.get("stroke-width")) for t in tangents}) == 1
    assert all(t.get("stroke-dasharray") for t in tangents)
    assert {p.get("fill") for p in contacts} == {"#334155"}
    assert len({p.get("r") for p in contacts}) == 1
    assert all(
        node.get("font-family") == "Times New Roman,serif"
        for node in rendered.findall(".//{*}text")
        if (node.text or "").strip() == "−"
    )
    assert len(source.findall(".//{*}path")) > 10
    for tangent in tangents:
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
