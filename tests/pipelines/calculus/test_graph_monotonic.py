"""Reviewed source cases and boundary semantics for one shared sign-chart family."""

import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan, source_bytes

from solution_runner.pipelines.calculus import graph_monotonic as graph
from solution_runner.pipelines.calculus import graph_monotonic_chart, graph_value_order
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
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
            ("section:answer", "section:solution", "section:condition", "asset:")
        )
        for t in first.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>123456</p>"
    assert plan(case, context).answer == first.answer
    context = deepcopy(original)
    rewritten_assets = {
        t["value"]["asset_key"]
        for t in first.transformations
        if t["transformation_target_id"].startswith("asset:")
        and t["operation"] == "rewrite"
    }
    source = None
    if rewritten_assets:
        handler = get_handler(get_group_profile(case["group"]).content_rule_key)
        source = next(
            s["svg_text"].encode()
            for s in handler.diagram_specs(
                context, condition_asset_bytes=source_bytes(case)
            )
            if s["asset_key"] in rewritten_assets
        )
    _apply_local(context, first.transformations)
    assert plan(case, context, source=source).transformations == ()


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
    assert (
        graph_monotonic_chart.compare(
            {"x_bounds": [1, 2], "x_bounds_open": [True, True]}, 2
        )
        == -1
    )


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


def test_unique_global_extremum_removes_the_previous_function_sketch():
    case = sample("508310")
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    solution = next(s for s in content["sections"] if s["key"] == "solution")
    sketch = "function_comparison_sketch"
    solution["asset_keys"].append(sketch)
    content["assets"].append({"asset_key": sketch, "asset_id": "previous-sketch"})

    result = plan(case, context)
    assert result.answer == "-2"
    assert {
        "operation": "remove",
        "transformation_target_id": "asset:" + sketch,
    } in result.transformations
    images = BeautifulSoup(result.solution_html, "html.parser").find_all("img")
    assert [image["data-asset-key"] for image in images] == ["monotonicity_sign_chart"]


def test_value_question_returns_ordinate_and_checks_every_candidate():
    data, question, bands = graph._input(sample("559401")["context"])
    assert graph.proof(question, bands, data[5])[0] == "-4"
    changed = deepcopy(data[5])
    changed["ordinate_points"] = [p for p in changed["ordinate_points"] if p["x"] != 6]
    with pytest.raises(ValueError, match="all endpoint"):
        graph.proof(question, bands, changed)


def test_comparison_uses_one_source_sketch_and_valid_latex():
    case = sample("505119")
    result = plan(case, case["context"])
    solution = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    images = BeautifulSoup(solution, "html.parser").find_all("img")
    assert images[0]["data-asset-key"] == "monotonicity_sign_chart"
    assert len(images) == 2
    assert (
        images[1]["data-asset-id"]
        == case["context"]["normalized_content"]["assets"][1]["asset_id"]
    )
    assert "Примечание" not in solution
    assert "Построим примерный график" in solution
    assert r"f(-5) \geq f(5)" in solution
    assert 'data-inline-latex="x=3"' in solution


@pytest.mark.parametrize("task", ("524604", "524605", "528116"))
def test_comparison_draws_function_with_the_stated_relationship(task):
    case = sample(task)
    context = case["context"]
    _, question, bands = graph._input(context)
    points, winner = graph_value_order.sketch_points(question, bands)
    heights = dict(points)
    a, operator, b = question.comparisons[0]
    if operator == "=":
        assert heights[a] == heights[b]
    else:
        assert operator == "<" and heights[a] < heights[b]
    extremum = max if question.target == "наибольшее" else min
    assert winner == -2
    assert heights[winner] == extremum(heights.values())
    sketch = next(
        spec
        for spec in graph.diagram_specs(
            context, condition_asset_bytes=source_bytes(case)
        )
        if spec["asset_key"] == "function_comparison_sketch"
    )
    root = ET.fromstring(sketch["svg_text"])
    assert "y = f(x)" in "".join(root.itertext())
    assert any(path.get("stroke") == "#143B8F" for path in root.findall("{*}path"))
    images = BeautifulSoup(plan(case, context).solution_html, "html.parser").find_all(
        "img"
    )
    assert [image["data-asset-key"] for image in images] == [
        "monotonicity_sign_chart",
        "function_comparison_sketch",
    ]


@pytest.mark.parametrize("task", ("551780", "551782", "551783"))
def test_monotonic_sum_removes_the_previous_function_example(task):
    case = sample(task)
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    solution = next(s for s in content["sections"] if s["key"] == "solution")
    if task == "551780":
        key = "image_2"
    else:
        key = "continuous_primitive"
        solution["asset_keys"].append(key)
        content["assets"].append({"asset_key": key, "asset_id": "previous-sketch"})

    result = plan(case, context)
    assert {
        "operation": "remove",
        "transformation_target_id": "asset:" + key,
    } in result.transformations
    images = BeautifulSoup(result.solution_html, "html.parser").find_all("img")
    assert [image["data-asset-key"] for image in images] == ["monotonicity_sign_chart"]
