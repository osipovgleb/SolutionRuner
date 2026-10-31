"""Explicit substitutions and inverse angles keep the original selection method."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import C, S, analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    angles,
    compare_q,
    decode,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_substitution.json"
    ).read_text()
)
CASES = DATA["cases"]
A = sp.acos(sp.Rational(1, 6)) / sp.pi
RESIDUES = {
    "509579": (0, sp.Rational(1, 3), sp.Rational(5, 3)),
    "509926": (sp.Rational(1, 6), sp.Rational(1, 2), sp.Rational(5, 6)),
    "509947": (sp.Rational(1, 6), sp.Rational(5, 6)),
    "509968": (sp.Rational(3, 4), sp.Rational(5, 4)),
    "515919": (
        sp.Rational(1, 6),
        sp.Rational(5, 6),
        sp.Rational(7, 6),
        sp.Rational(11, 6),
    ),
    "485935": (sp.Rational(2, 3), sp.Rational(4, 3)),
    "485940": (sp.Rational(1, 6), sp.Rational(5, 6)),
    "515724": (0, A, 2 - A),
    "510106": (sp.Rational(3, 4), sp.Rational(5, 4)),
    "500961": (
        sp.Rational(1, 6),
        sp.Rational(1, 2),
        sp.Rational(3, 2),
        sp.Rational(11, 6),
    ),
    "510337": (
        sp.Rational(1, 3),
        sp.Rational(1, 2),
        sp.Rational(3, 2),
        sp.Rational(5, 3),
    ),
    "510340": (
        sp.Rational(1, 2),
        sp.Rational(5, 6),
        sp.Rational(7, 6),
        sp.Rational(3, 2),
    ),
    "510733": (0, 1, sp.Rational(7, 6), sp.Rational(11, 6)),
    "513091": (sp.Rational(1, 6), sp.Rational(11, 6)),
}
SELECTED = {
    "509579": (-4, -sp.Rational(11, 3)),
    "509926": (sp.Rational(13, 6), sp.Rational(5, 2)),
    "509947": (sp.Rational(13, 6),),
    "509968": (-sp.Rational(11, 4),),
    "515919": (sp.Rational(7, 6), sp.Rational(11, 6), sp.Rational(13, 6)),
    "485935": (-sp.Rational(2, 3), sp.Rational(2, 3), sp.Rational(4, 3)),
    "485940": (sp.Rational(1, 6), sp.Rational(5, 6)),
    "515724": (-2 - A, -2, -2 + A),
    "510106": (-sp.Rational(11, 4),),
    "500961": (-sp.Rational(7, 2), -sp.Rational(5, 2), -sp.Rational(13, 6)),
    "510337": (-sp.Rational(3, 2), -sp.Rational(1, 2), -sp.Rational(1, 3)),
    "510340": (-sp.Rational(17, 6), -sp.Rational(5, 2), -sp.Rational(3, 2)),
    "510733": (-sp.Rational(13, 6), -2, -1),
    "513091": (sp.Rational(23, 6),),
}
X = sp.Symbol("x", real=True)
ORIGINAL = {
    "509579": sp.cos(2 * X) - 3 * sp.cos(X) + 2,
    "509926": sp.cos(2 * X) + 3 * sp.sin(X) - 2,
    "509947": 3 * sp.cos(2 * X) - 5 * sp.sin(X) + 1,
    "509968": sp.cos(2 * X) - 5 * sp.sqrt(2) * sp.cos(X) - 5,
    "515919": sp.cos(2 * X) + sp.sin(X) ** 2 - sp.Rational(3, 4),
    "485935": 6 * sp.cos(X) ** 2 - 7 * sp.cos(X) - 5,
    "485940": 4 * sp.sin(X) ** 2 - 12 * sp.sin(X) + 5,
    "515724": 6 * sp.sin(X) ** 2 + 7 * sp.cos(X) - 7,
    "510106": sp.cos(2 * X) - 5 * sp.sqrt(2) * sp.cos(X) - 5,
    "500961": 2 * sp.sin(3 * sp.pi / 2 + X) ** 2 - sp.sqrt(3) * sp.cos(X),
    "510337": 2 * sp.sin(3 * sp.pi / 2 - X) ** 2 - sp.cos(X),
    "510340": 2 * sp.sin(sp.pi / 2 + X) ** 2 + sp.sqrt(3) * sp.cos(X),
    "510733": 2 * sp.sin(X) ** 2 - sp.cos(3 * sp.pi / 2 - X),
    "513091": 2 * sp.cos(2 * X) + 4 * sp.sqrt(3) * sp.cos(X) - 7,
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def analysis(c, context=None):
    _, formula, interval, bounds = read(context or c["context"])
    return analyze(formula, interval, bounds, parent(c))


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_six_more_groups_extend_the_existing_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 4, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_root_sets_and_independently_written_original_equations(c):
    a = analysis(c)
    assert a.residues == RESIDUES[c["task"]] and a.selected == SELECTED[c["task"]]
    for q in (*a.residues, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, sp.expand(q * sp.pi))) == 0
    grid = tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi * i / 12)) == 0
    )
    assert grid == ((0,) if c["task"] == "515724" else a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_and_solutions_are_unused_and_replay_is_empty(c):
    context = deepcopy(c["context"])
    before = deepcopy(context)
    p = plan(c, context)
    assert context == before and p.condition_html == next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    for s in context["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>INVALID999999</p>"
    assert plan(c, context) == p
    for t in p.transformations:
        s = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        s.update(t["value"])
    assert plan(c, context).transformations == ()
    assert (
        context["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_numbers_do_not_supply_child_values(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    for span in soup.select("[data-inline-latex]"):
        span["data-inline-latex"] = re.sub(r"\d+", "997", span["data-inline-latex"])
    assert plan(c, prototype=str(soup)) == plan(c)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_instructions_parent_or_assets_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype="")
    context = deepcopy(c["context"])
    context["normalized_content"]["assets"].append({"asset_key": "unknown"})
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = s["html"].replace("Ре­ши­те", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "task,variable",
    [("515919", "t"), ("485935", "y"), ("485940", "y"), ("515724", "y")],
)
def test_explicit_substitution_and_back_substitution_precede_selection(task, variable):
    c = case(task)
    a = analysis(c)
    assert a.substitution == variable
    html = plan(c).solution_html
    soup = BeautifulSoup(html, "html.parser")
    formulas = [s["data-inline-latex"] for s in soup.select("[data-inline-latex]")]
    assert any(f.startswith(variable + "=") for f in formulas)
    assert (
        html.index("Введём обозначение")
        < html.index("Вернёмся к исходной переменной")
        < html.index(
            "Найдём корни" if task != "515919" else "С помощью числовой окружности"
        )
    )
    assert a.selection_method == ("circle" if task == "515919" else "inequalities")


def test_inequalities_use_the_exact_original_integer_parameter_ranges():
    a = analysis(case("485935"))
    assert [(offset, start, end) for offset, _, start, end, _ in a.selections] == [
        (-sp.Rational(2, 3), 0, 1),
        (sp.Rational(2, 3), 0, 0),
    ]
    a = analysis(case("515724"))
    assert all(start == -1 and end == -1 for _, _, start, end, _ in a.selections)
    assert all(period == 2 for _, period, _, _, _ in a.selections)
    assert {v for b in a.branches for v in b.values} == {1, sp.Rational(1, 6)}
    html = plan(case("515724")).solution_html
    assert r"\arccos" in html and "operatorname{acos}" not in html


@pytest.mark.parametrize(
    "boundary,expected",
    [
        (sp.Rational(-1), 1),
        (0, 1),
        (sp.Rational(1, 3), 1),
        (sp.Rational(1, 2), -1),
        (1, -1),
        (2, -1),
    ],
)
def test_inverse_angles_are_compared_by_monotonicity_without_floating_point(
    boundary, expected
):
    assert compare_q(A, sp.sympify(boundary)) == expected
    assert compare_q(sp.sympify(boundary), A) == -expected
    assert compare_q(A, A) == 0


def test_inverse_series_keep_closed_zero_and_exclude_open_zero():
    series = ((0, sp.Integer(2)), (A, sp.Integer(2)))
    assert select(series, (sp.Integer(0), sp.Integer(1), True, True))[0] == (0, A)
    assert select(series, (sp.Integer(0), sp.Integer(1), False, True))[0] == (A,)
    assert select(series, (sp.Integer(0), sp.Integer(0), True, True))[0] == (0,)


def test_principal_sine_angles_keep_both_negative_sine_branches():
    q = angles(S, -sp.Rational(1, 6), True)
    assert len(q) == 2
    for root in q:
        assert sp.simplify(sp.sin(sp.expand(root * sp.pi)) + sp.Rational(1, 6)) == 0
    with pytest.raises(UnsupportedCondition):
        angles(C, sp.Rational(1, 6), False)


def test_multiple_independent_inverse_angles_fail_closed():
    with pytest.raises(UnsupportedCondition):
        compare_q(A, sp.acos(sp.Rational(1, 5)) / sp.pi)


def test_unknown_inverse_label_schema_or_wrong_audited_value_fail_closed():
    with pytest.raises(UnsupportedCondition):
        decode({"acos": "1/6", "rational": "0", "coefficient": 0})
    a = analysis(case("515724"))
    entry = deepcopy(CIRCLES["31d13492-4980-440a-8b35-b90f72e96dcc"])
    entry["residues"][1]["acos"] = "1/5"
    with pytest.raises(UnsupportedCondition):
        validate(entry, a)


def test_no_figure_is_invented_for_figureless_source_tasks_and_child_circle_is_retained():
    for task in ("485935", "485940"):
        c = case(task)
        assert (
            get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
                c["context"]
            )
            == ()
        )
        assert "<img" not in plan(c).solution_html
    c = case("515724")
    html = plan(c).solution_html
    soup = BeautifulSoup(html, "html.parser")
    image = soup.find("img")
    assert image["data-asset-id"] == "31d13492-4980-440a-8b35-b90f72e96dcc"
    assert image.find_parent("li")["data-list-marker"] == "а)"
    assert html.index("<img") < html.index("Решим неравенства")


@pytest.mark.parametrize("task", ["509926", "509947", "485940", "510733"])
def test_changed_linear_function_uses_the_corresponding_quadratic(task):
    a = analysis(case(task))
    assert len(a.branches) == 1 and a.branches[0].variable == S and a.preferred == S


def test_missing_source_fragments_do_not_leak_into_prepared_solutions():
    for task in ("510337", "510340"):
        html = plan(case(task)).solution_html
        assert "Not match" not in html


@pytest.mark.parametrize("value", [-2, 2])
def test_inverse_angle_values_outside_the_unit_range_fail_closed(value):
    with pytest.raises(UnsupportedCondition):
        angles(C, sp.Integer(value), True)
