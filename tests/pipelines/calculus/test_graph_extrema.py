"""Function extrema and derivative zeros: source samples and strict selection."""

import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import graph_extrema as graph
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
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
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
    assert (
        len(BeautifulSoup(html, "html.parser").find_all("img"))
        == len(original["normalized_content"]["assets"]) - 1
    )


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


def test_same_curve_uses_the_exact_existing_minimum_figure_after_switching_kind():
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
    minimum = graph._input(context)[2]["solution_asset"]["source_id"]
    assert BeautifulSoup(solution, "html.parser").img["data-asset-id"] == minimum


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
    with pytest.raises(ValueError, match="graph role"):
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
    assert "N_{\\min}=1" in formulas
    assert not any("x_{1}" in formula for formula in formulas)
