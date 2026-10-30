"""Live derivative levels and independent crossing/tangency geometry checks."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import curve_levels
from solution_runner.pipelines.calculus import graph_derivative_levels as graph
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_levels.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_live_registration_reuses_one_derivative_graph_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == "calculus-graph-derivative-level"
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_assets_and_idempotence_are_independent(case):
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
    data, q, entry, points, result = graph._input(original)
    assert result == first.answer
    assert len(points) == curve_levels.count(entry["curve_nodes"], q.slope)
    solution = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert len(BeautifulSoup(solution, "html.parser").find_all("img")) == int(
        entry["diagram_style"] != "none"
    )
    assert data[5]["curve_name"] == "derivative"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unparsed_instructions_and_changed_svg_bytes_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Точки касания уровня не учитывайте.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"another derivative graph")


def _cubic():
    # In Cartesian coordinates this curve is y=x^3-x on (-2,2).
    return {
        "svg_origin": [0, 0],
        "svg_unit": 1,
        "curve_nodes": [
            {"svg": [-2, 6], "y": -6, "endpoint": True},
            {"svg": [-0.577350269, -0.384900179], "y_bounds": [".38", ".39"]},
            {"svg": [0.577350269, 0.384900179], "y_bounds": ["-.39", "-.38"]},
            {"svg": [2, -6], "y": 6, "endpoint": True},
        ],
        "curve_segments": [[[-2, 6], [-2 / 3, -26 / 3], [2 / 3, 26 / 3], [2, -6]]],
    }


def test_cubic_crossings_are_computed_from_controls_and_monotone_arcs():
    entry = _cubic()
    assert [p[0] for p in curve_levels.intersections(entry, 0)] == pytest.approx(
        [-1, 0, 1]
    )
    (point,) = curve_levels.intersections(entry, 1)
    assert point[0] ** 3 - point[0] == pytest.approx(1)
    assert curve_levels.count(entry["curve_nodes"], 1) == 1


def test_level_tangent_at_a_vertex_is_counted_once_and_open_endpoints_are_excluded():
    entry = {
        "svg_origin": [0, 0],
        "svg_unit": 1,
        "curve_nodes": [
            {"svg": [0, -2], "y": 2, "endpoint": True},
            {"svg": [1, -3], "y": 3},
            {"svg": [2, -2], "y": 2, "endpoint": True},
        ],
        "curve_segments": [[[0, -2], [2 / 3, -10 / 3], [4 / 3, -10 / 3], [2, -2]]],
    }
    assert curve_levels.intersections(entry, 3) == pytest.approx([(1, -3)])
    assert curve_levels.intersections(entry, 2) == []
    assert len(curve_levels.intersections(entry, 2.5)) == 2


def test_unknown_vertex_ordinate_and_constant_level_segments_are_refused():
    entry = _cubic()
    with pytest.raises(ValueError, match="does not resolve"):
        curve_levels.intersections(entry, 0.385)
    with pytest.raises(ValueError, match="infinitely many"):
        curve_levels.count([{"svg": [0, 0], "y": 2}, {"svg": [1, 0], "y": 2}], 2)


def test_inconsistent_curve_controls_cannot_create_a_plausible_count():
    entry = _cubic()
    entry["curve_segments"] = [[[0, 1], [1 / 3, 1], [2 / 3, 1], [1, 1]]]
    with pytest.raises(ValueError, match="disagree"):
        curve_levels.intersections(entry, 0)


def test_changed_level_replaces_incompatible_annotation_instead_of_copying_it():
    case = next(c for c in CASES if c["task"] == "27501")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    image = str(BeautifulSoup(condition["html"], "html.parser").find("img"))
    condition["html"] = (
        "<p>На рисунке изображен график производной функции f(x), определенной на интервале (-10;2). Найдите количество точек, в которых касательная к графику функции f(x) параллельна прямой y=7 или совпадает с ней.</p>"
        + image
    )
    original = deepcopy(context)
    result = plan(case, context)
    assert result.answer == "3"
    assert context == original
    assert any(
        t["operation"] == "remove" and t["transformation_target_id"] == "asset:image_2"
        for t in result.transformations
    )
    assert graph.diagram_specs(context)
    _apply_local(context, result.transformations)
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize(
    "task,old,new",
    [("27501", "производной", "самой"), ("40131", "абсциссу", "ординату")],
)
def test_graph_role_or_requested_quantity_cannot_be_discarded(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    # Source text contains soft hyphens; rewrite only that display convention.
    condition["html"] = condition["html"].replace("\u00ad", "")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    with pytest.raises(ValueError):
        plan(case, context)


def test_prepared_level_lines_preserve_source_geometry_and_stay_behind_its_labels():
    import xml.etree.ElementTree as ET

    for case in CASES:
        data, q, entry, points, _ = graph._input(case["context"])
        for spec in graph.diagram_specs(case["context"]):
            before, after = ET.fromstring(data[6]), ET.fromstring(spec["svg_text"])
            assert before.attrib == after.attrib
            originals = [
                n
                for n in after
                if not n.get("data-runner-layer") and not n.get("data-runner-diagram")
            ]
            assert [ET.tostring(n) for n in before] == [
                ET.tostring(n) for n in originals
            ]
            assert (
                list(after)[entry["svg_level_layer"]].get("data-runner-layer")
                == "level"
            )
            foreground = list(after)[-1]
            assert foreground.get("data-runner-diagram") == "derivative_level"
            circles = [n for n in foreground if n.tag.endswith("circle")]
            assert len(circles) == len(points)
            y = entry["svg_origin"][1] - float(q.slope) * entry["svg_unit"]
            assert all(float(n.get("cy")) == pytest.approx(y) for n in circles)
