"""Reviewed source cases and boundary semantics for one shared sign-chart family."""

import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import graph_monotonic as graph
from solution_runner.pipelines.calculus import graph_monotonic_chart, graph_value_order
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_monotonic.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_group_registration(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == group["rule"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_answers_are_computed_plans_are_local_and_idempotent(case):
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
def test_unread_instructions_or_changed_downloads_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Граничные точки не учитывайте.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"changed source")


def test_zero_is_included_in_monotonic_interval_but_not_strict_derivative_count():
    case = sample("6429")
    data, question, bands = graph._input(case["context"])
    increasing = [b for b in bands if b[4] > 0]
    assert graph.integers(increasing, question.domain) == [2, 3, 4, 5]
    strict = graph.chart(data[5], replace(question, operation="count"))
    assert graph.integers([b for b in strict if b[4] > 0], question.domain) == [3, 4, 5]


def test_continuity_joins_same_sign_branches_across_an_undefined_derivative():
    data, question, bands = graph._input(sample("551780")["context"])
    assert len(bands) == 1
    assert graph.integers(bands, question.domain) == [-2, -1, 0, 1, 2, 3]
    separated = graph.chart(data[5], replace(question, continuous=False))
    assert len(separated) == 2
    assert graph.integers(separated, question.domain) == [-2, -1, 0, 2, 3]


def test_continuity_includes_the_corner_in_each_monotonic_branch():
    _, question, bands = graph._input(sample("551782")["context"])
    assert graph.integers([bands[0]], question.domain) == [-4, -3, -2, -1]
    assert graph.integers([bands[1]], question.domain) == [-1, 0, 1, 2, 3, 4]


def test_closed_function_domain_is_independent_of_open_derivative_end_markers():
    _, question, bands = graph._input(sample("551737")["context"])
    assert graph.integers([b for b in bands if b[4] > 0], question.domain) == [
        -6,
        2,
        3,
        4,
        5,
    ]
    assert question.domain.lower_closed and question.domain.upper_closed


def test_ambiguous_integer_boundary_is_refused_without_rounding():
    with pytest.raises(ValueError, match="resolve"):
        graph_monotonic_chart.compare({"x_bounds": ["3/2", "5/2"]}, 2)
    assert graph_monotonic_chart.compare({"x_bounds": [1, 2], "x_bounds_open": [True, True]}, 2) == -1


def test_approximate_shorter_interval_does_not_prevent_exact_longest_length():
    case = sample("628266")
    assert plan(case, case["context"]).answer == "4"
    data, question, _ = graph._input(case["context"])
    changed = deepcopy(data[5])
    changed["monotonic_points"][1] = {
        **changed["monotonic_points"][1],
        "x_bounds": [-6, -4],
    }
    del changed["monotonic_points"][1]["x"]
    with pytest.raises(ValueError, match="longest"):
        graph.proof(question, graph.chart(changed, question), changed)


def test_global_extrema_do_not_follow_from_local_sign_changes_alone():
    _, question, bands = graph._input(sample("524604")["context"])
    assert graph_value_order.extremum(question, bands)[0] == -2
    with pytest.raises(ValueError, match="unique global"):
        graph_value_order.extremum(replace(question, comparisons=()), bands)
    with pytest.raises(ValueError, match="contradict"):
        graph_value_order.extremum(
            replace(question, comparisons=((Fraction(-2), "=", Fraction(1)),)), bands
        )
    with pytest.raises(ValueError, match="open endpoint"):
        graph_value_order.extremum(
            replace(question, comparisons=((Fraction(-4), "=", Fraction(3)),)), bands
        )


def test_open_endpoint_cannot_become_the_location_of_a_global_extremum():
    _, question, bands = graph._input(sample("508310")["context"])
    span = graph.interval("(-6;-3)")
    with pytest.raises(ValueError, match="not included"):
        graph.global_point(replace(question, span=span), bands)


def test_value_question_returns_ordinate_and_checks_every_candidate():
    data, question, bands = graph._input(sample("559401")["context"])
    assert graph.proof(question, bands, data[5])[0] == "-4"
    changed = deepcopy(data[5])
    changed["ordinate_points"] = [p for p in changed["ordinate_points"] if p["x"] != 6]
    with pytest.raises(ValueError, match="all endpoint"):
        graph.proof(question, bands, changed)


def test_exact_source_illustrations_and_continuity_counterexample_are_preserved():
    case = sample("505119")
    result = plan(case, case["context"])
    solution = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    images = BeautifulSoup(solution, "html.parser").find_all("img")
    assert [img["data-asset-id"] for img in images] == [
        a["asset_id"] for a in case["context"]["normalized_content"]["assets"][1:]
    ]
    assert "Непрерывность на концах существенна" in solution
    assert "99,9999" not in solution
    assert "f(3)&lt;f(5)" in solution


def test_primitive_example_has_a_continuous_minimum_and_correct_endpoint_markers():
    a = graph.diagram_specs(sample("551782")["context"])[0]
    b = graph.diagram_specs(sample("551783")["context"])[0]
    assert a == b
    root = ET.fromstring(a["svg_text"])
    circles = root.findall("{*}circle")
    assert [c.get("fill") for c in circles] == ["#143B8F", "#143B8F", "white"]
    points = [
        tuple(map(float, p.split(",")))
        for p in next(
            p for p in root.findall("{*}path") if p.get("stroke") == "#143B8F"
        )
        .get("d")
        .replace("M", "")
        .replace("L", "")
        .split()
    ]
    # SVG y grows downward: the corner B is the lowest value of the function.
    bottom = max(y for _, y in points)
    corner_x = float(circles[1].get("cx"))
    assert all(abs(x - corner_x) < 0.01 for x, y in points if abs(y - bottom) < 0.001)
    assert not any("999999" in text for text in root.itertext())
