"""All trig graphs use exact inspected scales, visible points and parent methods."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan, replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import trig_graph, trig_svg
from solution_runner.pipelines.function_graphs.linear_svg import NS, frame
from solution_runner.pipelines.function_graphs.parabola_svg import segments

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_trig.json").read_text()
)
CASES = DATA["cases"]


def changed(case, edit):
    context = deepcopy(case["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = edit(s["html"])
    return context


def result_soup(result):
    return BeautifulSoup(
        next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"] == "section:solution:1"
        ),
        "html.parser",
    )


def points(case):
    q = trig_graph.parse(case["context"])
    return trig_svg.read(
        case["context"],
        (ROOT / case["condition_file"]).read_bytes(),
        "image/svg+xml",
        q.function,
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_eight_profiles_share_one_handler(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "trigonometric-function-graph"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 5
    assert (
        p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        and p.category_key == "12"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_uses_only_condition_and_preserves_every_figure(case):
    original = deepcopy(case["context"])
    result = plan(case)
    saved = next(
        s["html"]
        for s in original["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    context = deepcopy(original)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    altered = plan(case, context)
    assert altered.answer == result.answer and result_soup(altered) == result_soup(
        result
    )
    assert case["context"] == original
    updated = replay(original, result.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    assert {t["transformation_target_id"] for t in result.transformations} <= {
        "section:answer:1",
        "section:solution:1",
    }
    assert all(
        s in updated["normalized_content"]["sections"]
        for s in original["normalized_content"]["sections"]
        if s["key"] not in {"answer", "solution"}
    )
    assert (
        hashlib.sha256((ROOT / case["condition_file"]).read_bytes()).hexdigest()
        == case["condition_sha256"]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_zero_value_then_coefficient_then_periodic_value_follow_parent_method(case):
    q = trig_graph.parse(case["context"])
    soup = result_soup(plan(case))
    assert len(
        soup.select('section[data-content-kind="solution"]')
    ) == 1 and not soup.select("img")
    forms = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert forms[0].startswith("f(") and forms[1].endswith("=0")
    assert "b=" in forms[3]
    assert len(forms) == (4 if q.kind == "b" else 9 if q.kind == "a" else 13)
    if q.kind != "b":
        assert forms[4].startswith("f(") and forms[8].startswith("a=")
    if q.kind == "value":
        assert forms[9].startswith("y=") and forms[-1].startswith("y(")
        assert "период 2π" in soup.get_text()
    assert "одна клетка" in soup.get_text() and "1/2" in soup.get_text()
    assert r"\qquadf" not in str(soup)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "edit",
    [
        lambda h: "<p>Дополнительное условие.</p>" + h,
        lambda h: h + '<span data-inline-latex="a=2"></span>',
        lambda h: h + '<img src="extra.svg"/>',
        lambda h: h.replace("f(x)=", "g(x)=", 1),
        lambda h: h.replace('data-asset-key="image_1"', 'data-asset-key="image_2"'),
    ],
)
def test_entire_question_and_canonical_image_are_required(case, edit):
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, edit))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("kind", ["bytes", "mime", "solution_figure"])
def test_unknown_or_foreign_assets_fail_closed(case, kind):
    if kind == "bytes":
        with pytest.raises(ContentPlanError):
            plan(case, data=(ROOT / case["condition_file"]).read_bytes() + b" ")
    elif kind == "mime":
        with pytest.raises(ContentPlanError):
            plan(case, mime="image/png")
    else:
        context = deepcopy(case["context"])
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        )["html"] = '<img src="extra.svg"/>'
        with pytest.raises(ContentPlanError):
            plan(case, context)


@pytest.mark.parametrize(
    "task,coefficient,shift",
    [
        ("509123", sp.Rational(3, 2), -1),
        ("509126", -2, 1),
        ("509137", 2, sp.Rational(-3, 2)),
        ("509139", -2, sp.Rational(3, 2)),
        ("509290", sp.Rational(1, 2), 2),
        ("676854", 2, 1),
        ("676931", -2, -1),
    ],
)
def test_half_unit_grid_is_used_even_for_declared_integer_coefficients(
    task, coefficient, shift
):
    case = next(c for c in CASES if c["task"] == task)
    a = trig_graph.analyze(trig_graph.parse(case["context"]), points(case))
    assert (a.coefficient, a.shift) == (coefficient, shift)


@pytest.mark.parametrize("task", ["509138", "509139", "509140", "509143"])
def test_clipped_export_marker_is_excluded_and_dashed_asymptotes_are_not_axes(task):
    case = next(c for c in CASES if c["task"] == task)
    root = ET.fromstring((ROOT / case["condition_file"]).read_bytes())
    assert len(list(root.iter(NS + "circle"))) == 3 and len(points(case)) == 2
    frame(root)


@pytest.mark.parametrize("problem", ["units", "outside_count", "read_point"])
def test_inspection_metadata_cannot_override_geometry(problem, tmp_path, monkeypatch):
    case = next(c for c in CASES if c["task"] == "509138")
    data = (ROOT / case["condition_file"]).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    entry = json.loads((trig_svg.ASSET_DIR / "source-evidence.json").read_text())[sha]
    if problem == "units":
        entry["grid_unit"] = ["pi/2", "1"]
    elif problem == "outside_count":
        entry["outside_marker_count"] = 0
    else:
        entry["read_points"] = [[0, 0]]
    (tmp_path / "source-evidence.json").write_text(json.dumps({sha: entry}))
    monkeypatch.setattr(trig_svg, "ASSET_DIR", tmp_path)
    with pytest.raises(ContentPlanError):
        plan(case)


def test_explicit_integer_constraint_rejects_fractional_coefficients():
    case = CASES[0]
    with pytest.raises(ContentPlanError):
        trig_graph.analyze(
            trig_graph.Question("cos", "value", True, 13 * sp.pi / 3), points(case)
        )


@pytest.mark.parametrize(
    "task,coefficient,expected",
    [
        ("676854", sp.Rational(-1, 3), 2),
        ("676854", sp.Integer(1), -1),
        ("676931", sp.Rational(-1, 6), 0),
        ("676931", sp.Rational(7, 6), 0),
    ],
)
def test_negative_and_multiple_period_arguments_are_exact(task, coefficient, expected):
    case = next(c for c in CASES if c["task"] == task)
    a = trig_graph.analyze(
        trig_graph.Question(
            trig_graph.parse(case["context"]).function,
            "value",
            True,
            coefficient * sp.pi,
        ),
        points(case),
    )
    assert a.result == expected


@pytest.mark.parametrize(
    "function,target,ps",
    [
        ("cos", sp.pi / 4, [(0, 3), (-sp.pi / 2, 1)]),
        ("tan", sp.pi / 2, [(0, 1), (sp.pi / 4, 3)]),
    ],
)
def test_irrational_answers_and_tangent_poles_fail_closed(function, target, ps):
    with pytest.raises(ContentPlanError):
        trig_graph.analyze(
            trig_graph.Question(function, "value", True, target),
            [(x, sp.Integer(y)) for x, y in ps],
        )


def test_all_markers_must_match_one_formula():
    with pytest.raises(ContentPlanError):
        trig_graph.analyze(
            trig_graph.Question("sin", "a"),
            [
                (sp.Integer(0), sp.Integer(1)),
                (sp.pi / 2, sp.Integer(3)),
                (sp.pi, sp.Integer(2)),
            ],
        )


def test_relative_svg_lines_become_exact_cubics_and_reset_smooth_control():
    result = segments("M0,0 C1,2 2,2 3,0 l3,0 s2,2 3,0")
    assert result[1] == [[3, 0], [4, 0], [5, 0], [6, 0]]
    assert result[2] == [[6, 0], [6, 0], [8, 2], [9, 0]]
