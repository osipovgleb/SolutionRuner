"""Verify substitution branches, reciprocal bases and deliberate source-figure omission."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_inequality_planner import (
    build_context_repair_plan,
)
from solution_runner.pipelines.equations.logarithm_quadratic_inequality import analyze
from solution_runner.pipelines.equations.logarithm_quadratic_inequality_proof import (
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_quadratic_substitution_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for row in ROWS
    if row["task"] == row["group"]
    for s in row["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
EXPECTED = {
    "509503": sp.Union(
        sp.Interval.Lopen(-5, -2 * sp.sqrt(5)),
        sp.FiniteSet(0),
        sp.Interval.Ropen(2 * sp.sqrt(5), 5),
    ),
    "509890": sp.Union(sp.Interval.open(-1, 0), sp.Interval.open(3, 4)),
    "513260": sp.Union(
        sp.Interval.Lopen(-sp.Rational(21, 5), -sp.Rational(79, 20)),
        sp.Interval(sp.Rational(19, 5), sp.oo),
    ),
    "514254": sp.Union(sp.Interval.open(-2, 0), sp.Interval.open(6, 8)),
    "516800": sp.Union(
        sp.Interval.Lopen(-5, -sp.sqrt(22)),
        sp.Interval(-4, 4),
        sp.Interval.Ropen(sp.sqrt(22), 5),
    ),
}


def handler():
    return get_handler(get_group_profile("509503").content_rule_key)


def plan(ctx, parent=PARENT):
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


def model(row):
    return analyze(read_formula(row["context"])[1])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_source_answers_and_independent_argument_domains(row):
    a = model(row)
    same_set(a.solution, EXPECTED[row["task"]])
    same_set(answer_set(row["expected_answer"]), a.solution)
    same_set(
        a.domain, sp.solve_univariate_inequality(a.argument > 0, X, relational=False)
    )
    assert a.reciprocal_base == (row["task"] in ("509890", "514254"))
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_numerics_include_domains_and_exact_boundaries(row):
    task = row["task"]
    argument, base, linear, constant = {
        "509503": (25 - X**2, 5, -3, 2),
        "509890": (4 + 3 * X - X**2, 2, 7, 10),
        "513260": (X + sp.Rational(21, 5), 2, -1, -6),
        "514254": (16 + 6 * X - X**2, 2, 10, 24),
        "516800": (25 - X**2, 3, -3, 2),
    }[task]
    a = model(row)
    for value in (
        -6,
        -5,
        -sp.sqrt(22),
        -2 * sp.sqrt(5),
        -4,
        -1,
        0,
        1,
        3,
        4,
        5,
        6,
        7,
        8,
        2 * sp.sqrt(5),
        sp.sqrt(22),
        -sp.Rational(79, 20),
        sp.Rational(19, 5),
    ):
        arg = sp.simplify(argument.subs(X, value))
        if arg <= 0:
            assert a.solution.contains(value) is sp.false
            continue
        first = sp.log(arg) / sp.log(base)
        second = sp.log(arg) / sp.log(
            sp.Rational(1, base) if a.reciprocal_base else base
        )
        direct = sp.N(sp.simplify(first**2 + linear * second + constant), 50)
        strict = task in ("509890", "514254")
        assert bool(a.solution.contains(value)) == bool(
            direct > 0 if strict else direct >= 0
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_preparation_and_replay_preserve_conditions_and_assets(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(ctx)
    assert ctx == before and not handler().diagram_specs(ctx)
    assert "t=" in p.solution_html and "<img " not in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert not plan(ctx).transformations
    solution = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "solution"
    )
    assert solution["asset_keys"] == []


@pytest.mark.parametrize(
    "task,extreme", [("509890", sp.Rational(-103, 4)), ("514254", sp.Integer(-39))]
)
def test_reciprocal_conversion_and_impossible_branch_have_exact_justification(
    task, extreme
):
    row = next(v for v in ROWS if v["task"] == task)
    a = model(row)
    p = plan(row["context"])
    assert r"\log_{\frac{1}{2}}" in p.solution_html
    assert (
        "всегда отрицательна" in p.solution_html
        and sp.latex(extreme).removeprefix("-") in p.solution_html
    )
    branch = next(b for b in a.branches if b.solution == sp.EmptySet)
    c = branch.conditions[0]
    poly = sp.Poly(c.stage.original, X)
    vertex = -poly.nth(1) / (2 * poly.nth(2))
    assert poly.eval(vertex) == extreme and poly.nth(2) == -1
    same_set(
        sp.solve_univariate_inequality(c.stage.original > 0, X, relational=False),
        sp.EmptySet,
    )


def test_alternative_branches_are_not_conjoined_and_isolated_zero_is_retained():
    row = next(v for v in ROWS if v["task"] == "516800")
    a = model(row)
    assert sp.Intersection(*(b.solution for b in a.branches)) == sp.EmptySet
    same_set(sp.Union(*(b.solution for b in a.branches)), EXPECTED["516800"])
    soup = BeautifulSoup(plan(row["context"]).solution_html, "html.parser")
    systems = [
        s["data-inline-latex"]
        for s in soup.select("[data-inline-latex]")
        if r"\begin{cases}" in s["data-inline-latex"]
    ]
    assert len(systems) == 2 and all(r"\left[\begin{aligned}" in s for s in systems)
    assert r"\le3" in systems[0] and r"\ge9" in systems[0]
    assert all(s.count(r"\begin{cases}") == 1 for s in systems)
    assert (
        model(next(v for v in ROWS if v["task"] == "509503")).solution.contains(0)
        is sp.true
    )


def test_child_only_chart_is_omitted_without_mutating_or_relabelling_its_asset():
    row = next(v for v in ROWS if v["task"] == "513260")
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    assert len(ctx["normalized_content"]["assets"]) == 1
    p = plan(ctx)
    assert (
        "0f841f8d-342c-42d4-bca5-3c6c79713091" not in p.solution_html and ctx == before
    )
    ctx["normalized_content"]["assets"] = []
    assert plan(ctx).solution_html == p.solution_html


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_id", "foreign"),
        ("url", "/assets/foreign"),
        ("kind", "foreign"),
        ("asset_key", "foreign"),
    ],
)
def test_unreviewed_child_assets_fail_closed(field, value):
    ctx = deepcopy(next(v for v in ROWS if v["task"] == "513260")["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ctx)


def test_source_figure_cannot_move_into_the_condition_or_be_duplicated():
    original = next(v for v in ROWS if v["task"] == "513260")["context"]
    ctx = deepcopy(original)
    condition = next(
        v for v in ctx["normalized_content"]["sections"] if v["key"] == "condition"
    )
    condition["asset_keys"] = ["image_1"]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
    ctx = deepcopy(original)
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(ctx)


def test_parent_presentation_is_pinned_and_source_answer_is_not_used():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "changed")
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(ctx, parent_solution_html=PARENT, method="quadratic")
    with pytest.raises(UnsupportedCondition):
        render(model(ROWS[0]), method="foreign")
    with pytest.raises(UnsupportedCondition):
        render(
            analyze(r"\log_2^2(-x^2-1)-3\log_2(-x^2-1)+2\ge0"),
            method="quadratic_substitution",
        )
    expected = plan(ctx).answer
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == expected
