"""Source stationary points, interval uncertainty and primitive/function semantics."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import graph_input
from solution_runner.pipelines.calculus import graph_stationary as graph
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_stationary.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_groups_share_one_stationary_point_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == "calculus-graph-stationary-points"
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_values_assets_and_idempotence_do_not_use_stored_answers(case):
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
        t["transformation_target_id"].startswith(
            ("section:answer", "section:solution", "asset:")
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
    _, _, _, _, _, entry, _ = graph_input.read_graph(original)
    solution = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert len(BeautifulSoup(solution, "html.parser").find_all("img")) == int(
        bool(entry.get("solution_asset") or entry.get("highlight_stationary"))
    )
    if entry["curve_name"] == "F":
        assert any(
            "F'(x)" in n["data-inline-latex"]
            for n in BeautifulSoup(solution, "html.parser").select(
                "[data-inline-latex]"
            )
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_changed_downloads_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>При подсчёте исключите минимумы.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"another graph")


@pytest.mark.parametrize(
    "span,expected",
    [
        ("(-1;3)", [0, 1, 2]),
        ("[-1;3]", [-1, 0, 1, 2, 3]),
        ("[-1;3)", [-1, 0, 1, 2]),
        ("(-1;3]", [0, 1, 2, 3]),
    ],
)
def test_exact_endpoints_obey_the_question_not_the_picture_style(span, expected):
    points = [{"x": x, "kind": "stationary"} for x in range(-1, 4)]
    assert [p["x"] for p in graph.select(points, graph.interval(span))] == expected


@pytest.mark.parametrize("span,expected", [("[0;3]", 1), ("[2;3]", 0), ("(0;1)", 0)])
def test_bounds_are_used_only_when_the_whole_position_is_determined(span, expected):
    assert (
        len(
            graph.select(
                [{"x_bounds": ["1.1", "1.2"], "kind": "min"}], graph.interval(span)
            )
        )
        == expected
    )


def test_uncertain_boundary_is_refused_even_if_both_bounds_are_outside_a_narrow_request():
    points = [{"x_bounds": ["1.1", "1.3"], "kind": "max"}]
    for span in ["[1.2;2]", "[0;1.2]", "[1.15;1.25]"]:
        with pytest.raises(ValueError, match="does not resolve"):
            graph.select(points, graph.interval(span))


def test_stationary_inflection_is_not_lost_when_counting_zero_derivatives():
    points = [
        {"x": 0, "kind": "min"},
        {"x": 1, "kind": "stationary"},
        {"x": 2, "kind": "max"},
    ]
    span = graph.interval("[-1;3]")
    selected = graph.select(points, span)
    question = graph.Question("count", graph.interval("(-2;4)"), span)
    value, html = graph.proof(question, selected)
    assert value == "3"
    assert "N_{\\mathrm{прочие}}=1" in html


@pytest.mark.parametrize(
    "points",
    [
        [{"x": 1, "kind": "max"}, {"x": 1, "kind": "min"}],
        [{"x_bounds": [0, 2], "kind": "max"}, {"x": 1, "kind": "min"}],
        [{"x_bounds": [2, 1], "kind": "min"}],
        [{"x": 1, "kind": "corner"}],
    ],
)
def test_degenerate_or_unordered_transcriptions_are_refused(points):
    with pytest.raises(ValueError):
        graph.select(points, graph.interval("[-3;4]"))


def test_source_root_on_closed_right_endpoint_is_counted():
    case = next(c for c in CASES if c["task"] == "323171")
    data, _q, selected = graph._input(case["context"])
    assert any(p.get("x") == 3 for p in selected)
    assert len(selected) == 7
    assert (
        len(
            graph.select(
                data[5]["stationary_points"],
                graph.Interval(Fraction(-1), Fraction(3), True, False),
            )
        )
        == 6
    )


@pytest.mark.parametrize(
    "task,before,after",
    [
        ("323077", "пер­во­об­раз­ных", "про­из­вод­ных"),
        ("562751", "(–&#8288;4; 4)", "(–&#8288;4; 5)"),
    ],
)
def test_a_changed_mathematical_role_or_domain_cannot_reuse_an_old_transcription(
    task, before, after
):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if task == "562751":
        # Preserve the original source markup and change only the endpoint.
        before, after = "4).", "5)."
    assert before in condition["html"]
    condition["html"] = condition["html"].replace(before, after)
    with pytest.raises(ValueError):
        plan(case, context)


def test_highlight_uses_only_selected_points_and_the_requested_boundaries():
    case = next(c for c in CASES if c["task"] == "672820")
    data, q, points = graph._input(case["context"])
    (spec,) = graph.diagram_specs(case["context"])
    before, after = ET.fromstring(data[6]), ET.fromstring(spec["svg_text"])
    assert before.attrib == after.attrib
    # The source curve is preserved geometrically; only its colour follows the parent.
    assert [n.get("d") for n in before.iter() if n.tag.endswith("path")] == [
        n.get("d") for n in after.iter() if n.tag.endswith("path")
    ]
    group = list(after)[-1]
    assert group.attrib["data-runner-diagram"] == "stationary_points"
    circles = [n for n in group if n.tag.endswith("circle")]
    assert len(circles) == 9
    assert {(float(n.get("cx")), float(n.get("cy"))) for n in circles} == {
        tuple(p["svg"]) for p in points
    }
    ox, _ = data[5]["svg_origin"]
    unit = data[5]["svg_unit"]
    for boundary, bracket in zip(
        [q.interval.lower, q.interval.upper], list(group)[:2], strict=True
    ):
        x = float(bracket.get("points").split()[1].split(",")[0])
        assert (x - ox) / unit == pytest.approx(float(boundary))


def test_strict_parallelism_excludes_coincident_horizontal_tangents():
    points = [{"x": 0, "y": 2, "kind": "min"}, {"x": 1, "y": 3, "kind": "max"}]
    assert graph.parallel_points(points, Fraction(2), False) == [points[1]]
    assert graph.parallel_points(points, Fraction(2), True) == points
    with pytest.raises(ValueError, match="resolve coincidence"):
        graph.parallel_points(
            [{"x": 0, "y_bounds": ["1.9", "2.1"], "kind": "min"}], Fraction(2), False
        )
