"""Function extrema and derivative zeros: source samples and strict selection."""

import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan, source_bytes

from solution_runner.pipelines.calculus import graph_extrema as graph
from solution_runner.pipelines.calculus import monotonic_sum_input, monotonic_sum_render
from solution_runner.pipelines.calculus.graph_stationary import interval, select
from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_extrema.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_groups_use_stationary_or_extremum_math_without_id_dispatch(group):
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
        BeautifulSoup(expected, "html.parser").get_text(strip=True)
    )
    assert context == original
    generated = get_group_profile(case["group"]).content_rule_key in (
        "calculus-derivative-monotonic-sum",
        "calculus-graph-extrema",
    )
    assert all(
        t["transformation_target_id"].startswith(
            ("section:answer", "section:solution", "section:condition", "asset:")
            if generated
            else ("section:answer", "section:solution", "section:condition")
        )
        for t in first.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert plan(case, context).answer == first.answer
    context = deepcopy(original)
    _apply_local(context, first.transformations)
    assert plan(case, context).transformations == ()
    html = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    images = BeautifulSoup(html, "html.parser").find_all("img")
    expected_count = (
        1 if generated else len(original["normalized_content"]["assets"]) - 1
    )
    assert len(images) == expected_count


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_changed_source_diagrams_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Точки минимума не учитывайте.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"different curve")


def test_given_extremum_search_interval_has_vertical_boundaries():
    case = next(case for case in CASES if case["task"] == "27502")
    traced = monotonic_sum_input.input(case["context"], source_bytes(case))
    svg = ET.fromstring(monotonic_sum_render.render(traced))
    overlay = svg.find('.//{*}g[@id="derivative-signs-and-integers"]')
    lines = overlay.findall('{*}line[@stroke="#2563eb"]')
    ox, _ = traced.entry["svg_origin"]
    unit = traced.entry.get("x_unit", traced.entry["svg_unit"])
    left, right = lines
    for boundary, x in ((left, ox - 2 * unit), (right, ox + 6 * unit)):
        assert float(boundary.get("x1")) == float(boundary.get("x2")) == x
        assert float(boundary.get("y1")) < float(boundary.get("y2"))


def _parabola_chart(left, right):
    # f'(x)=(x-1)^2 touches zero while staying positive on both sides.
    return {
        "svg_origin": [0, 0],
        "svg_unit": 1,
        "curve_segments": [[[0, -1], [2 / 3, 1 / 3], [4 / 3, 1 / 3], [2, -1]]],
        "zero_points": [
            {"x": 1, "svg": [1, 0], "left_sign": left, "right_sign": right}
        ],
    }


def test_touching_zero_without_a_sign_change_is_not_an_extremum():
    assert graph.derivative_extrema(_parabola_chart(1, 1)) == []


def test_sign_change_selects_the_kind_independently_of_the_requested_kind():
    case = next(c for c in CASES if c["task"] == "501188")
    _, question, entry, points = graph._input(case["context"])
    assert [p["kind"] for p in graph.derivative_extrema(entry)] == ["max", "min"]
    assert points[0]["x"] == 9
    assert question.target == "min"


def test_a_corrupted_zero_abscissa_cannot_still_pass_the_geometry_check():
    case = next(c for c in CASES if c["task"] == "501188")
    _, _, entry, _ = graph._input(case["context"])
    entry = deepcopy(entry)
    entry["zero_points"][0]["x"] = 5
    with pytest.raises(ValueError, match="grid abscissa"):
        graph.derivative_extrema(entry)


@pytest.mark.parametrize(
    "span,expected", [("(-4;7)", 2), ("[-4;0]", 1), ("[0;7]", 1), ("[-4;7]", 2)]
)
def test_schematic_open_position_bounds_do_not_invent_coordinates(span, expected):
    points = [
        {
            "svg": [1, 1],
            "x_bounds": [-4, 0],
            "x_bounds_open": [True, True],
            "kind": "max",
        },
        {
            "svg": [2, 1],
            "x_bounds": [0, 7],
            "x_bounds_open": [True, True],
            "kind": "min",
        },
    ]
    assert len(select(points, interval(span), svg_order=True)) == expected
    with pytest.raises(ValueError, match="does not resolve"):
        select(points, interval("(-2;7)"), svg_order=True)


def test_schematic_points_with_overlapping_bounds_still_have_to_be_distinct():
    points = [
        {
            "svg": [1, 1],
            "x_bounds": [-4, 0],
            "x_bounds_open": [True, True],
            "kind": "max",
        },
        {
            "svg": [1, 2],
            "x_bounds": [-4, 0],
            "x_bounds_open": [True, True],
            "kind": "min",
        },
    ]
    with pytest.raises(ValueError):
        select(points, interval("(-4;7)"), svg_order=True)


def test_same_curve_marks_minima_after_switching_kind():
    case = next(c for c in CASES if c["task"] == "523369")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        condition["html"].replace("\u00ad", "").replace("максимума", "минимума")
    )
    context = _with_required_assets(
        context, get_group_profile(case["group"]).content_rule_key
    )
    original = deepcopy(context)
    result = plan(case, context)
    assert result.answer == "5"
    assert original == context
    assert any(
        t["operation"] == "remove" and t["transformation_target_id"] == "asset:image_2"
        for t in result.transformations
    )
    _apply_local(context, result.transformations)
    assert plan(case, context).transformations == ()
    solution = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert (
        BeautifulSoup(solution, "html.parser").img["data-asset-key"]
        == "colored_function_extrema"
    )
    assert "с зелёного на красный" in solution


def test_function_and_derivative_graphs_cannot_be_interchanged():
    case = next(c for c in CASES if c["task"] == "27490")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    image = str(BeautifulSoup(condition["html"], "html.parser").find("img"))
    condition["html"] = (
        "<p>На рисунке изображен график производной функции f(x), определенной на интервале (-2;12). Найдите количество точек экстремума функции f(x) на отрезке [0;11].</p>"
        + image
    )
    with pytest.raises(ValueError, match="graph role|sign intervals"):
        plan(case, context)


def test_open_selection_endpoints_are_not_counted_as_local_extrema():
    span = graph.parse(
        "На рисунке изображен график производной функции f(x), определенной на интервале (-6;6). Найдите точку экстремума функции f(x) на интервале (-4;5)."
    )
    assert not span.interval.lower_closed and not span.interval.upper_closed
    points = [
        {"svg": [0, 0], "x": -4, "kind": "max"},
        {"svg": [1, 0], "x": 2, "kind": "min"},
        {"svg": [2, 0], "x": 5, "kind": "max"},
    ]
    assert [p["x"] for p in select(points, span.interval, svg_order=True)] == [2]
    assert Fraction(2) == select(points, span.interval, svg_order=True)[0]["x"]


def test_counting_does_not_invent_abscissa_labels_for_an_unmarked_zero():
    case = next(c for c in CASES if c["task"] == "6427")
    result = plan(case, case["context"])
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert "Их количество — " + result.answer in html
    assert not any("x_{1}" in formula for formula in formulas)
