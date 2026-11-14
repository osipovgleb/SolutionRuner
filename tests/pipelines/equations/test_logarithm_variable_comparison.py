"""Cancelled-base restrictions and cubic monotonicity without lost argument domains."""

import json
import math
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
from solution_runner.pipelines.equations.logarithm_variable_comparison import (
    cubic_comparison,
    quotient_comparison,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_variable_comparison_sources.json")
    .read_text()
)
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}
QUOTIENTS = {
    "508510": (X**2 - X, 1, 30, 1, X + 3),
    "508512": (X**2 + 2 * X, 1, 56, 2, X + 5),
    "511559": (X**2 + 2 * X, 2, 48, 3, X + 5),
}
CUBICS = {
    "508539": (X**3 - 8, X**3 + 2 * X - 13, sp.Rational(5, 2)),
    "508541": (X**3 - 1, X**3 + 2 * X - 4, sp.Rational(3, 2)),
    "511568": (X**3 - 1, X**3 + 3 * X - 7, sp.Integer(2)),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, ctx=None, parent=None):
    return handler(row).plan(
        PlanInput(
            row["context"] if ctx is None else ctx,
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
        )
    )


def model(row):
    return (
        quotient_comparison
        if row["method"] == "base_cancel_quotient"
        else cubic_comparison
    )(read_formula(row["context"])[1])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_manual_arguments_answers_and_independent_cas(row):
    a = model(row)
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert plan(row).answer == a.answer
    if row["task"] in QUOTIENTS:
        P, alpha, beta, c, G = QUOTIENTS[row["task"]]
        assert (
            a.P == P and a.alpha == alpha and a.beta == beta and a.c == c and a.G == G
        )
        rational = (X**2 - alpha * X - beta) / (X - c - 1)
        assert sp.cancel(a.stage.original - rational) == 0
        oracle = sp.solve_univariate_inequality(
            rational <= 0, X, relational=False
        ).intersect(sp.Interval.open(c, sp.oo))
        same_set(a.working_solution, oracle)
        A = alpha * P + beta
        B = P - c
        C = P**2
        full = (
            sp.Intersection(
                *(
                    sp.solve_univariate_inequality(v > 0, X, relational=False)
                    for v in (A, B, C, G)
                )
            )
            - sp.solveset(G - 1, X, domain=sp.S.Reals)
            - sp.solveset(B - 1, X, domain=sp.S.Reals)
        )
        same_set(a.domain, full)
    else:
        A, B, threshold = CUBICS[row["task"]]
        assert a.A == A and a.B == B and sp.degree(B - A) == 1
        oracle = sp.solve_univariate_inequality(
            A - B <= 0, X, relational=False
        ).intersect(sp.solve_univariate_inequality(A > 0, X, relational=False))
        same_set(a.solution, oracle)
        same_set(a.solution, sp.Interval(threshold, sp.oo))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_signs_and_every_argument_restriction(row):
    a = model(row)
    for point in (sp.Rational(i, 10) for i in range(-60, 61)):
        if row["task"] in QUOTIENTS:
            P, alpha, beta, c, G = QUOTIENTS[row["task"]]
            A = alpha * P + beta
            B = P - c
            C = P**2
            av, bv, cv, gv = [float(v.subs(X, point)) for v in (A, B, C, G)]
            valid = av > 0 and bv > 0 and cv > 0 and gv > 0 and gv != 1 and bv != 1
            value = (
                math.log(av, gv) / math.log(bv, gv)
                - math.log(cv, float(a.reference)) / math.log(bv, float(a.reference))
                if valid
                else 0
            )
            expected = valid and value >= -1e-8
        else:
            A, B, _ = CUBICS[row["task"]]
            av, bv = float(A.subs(X, point)), float(B.subs(X, point))
            valid = point > 0 and point != 1 and av > 0 and bv > 0
            value = (
                math.log(av, float(point)) - math.log(bv, float(point)) if valid else 0
            )
            expected = valid and value <= 1e-8
        assert bool(a.solution.contains(point)) == expected, (row["task"], point)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_parent_replay_has_no_condition_or_asset_writes(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and not handler(row).diagram_specs(ctx)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert (
        gateway.reads == [ctx["problem_id"]]
        and record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("task,hole", [("508510", -2), ("508512", -4), ("511559", -4)])
def test_cancelled_base_hole_remains_open_after_quadratic_inverse_and_parent_note(
    task, hole
):
    row = next(r for r in ROWS if r["task"] == task)
    a = model(row)
    assert (
        a.preimage.contains(hole) is sp.true
        and a.domain.contains(hole) is sp.false
        and a.solution.contains(hole) is sp.false
    )
    html = plan(row).solution_html
    formulas = [
        v["data-inline-latex"]
        for v in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    substitution = next(i for i, f in enumerate(formulas) if f.startswith("y="))
    assert substitution > next(i for i, f in enumerate(formulas) if r"\frac" in f)
    assert "Примечание" in html and "рационализац" in html
    assert not any(r"\lex" in f or r"\gex" in f for f in formulas)


@pytest.mark.parametrize(
    "row", [r for r in ROWS if r["group"] == "508539"], ids=lambda r: r["task"]
)
def test_cubic_second_argument_positive_by_comparison_and_first_base_always_increasing(
    row,
):
    a = model(row)
    assert a.first_stage.solution.is_subset(sp.Interval.open(1, sp.oo)) is True
    assert a.solution.is_subset(a.first_stage.solution) is True
    assert sp.degree(a.B) == 3 and sp.degree(a.stage.original) == 1
    assert "второй аргумент также положителен" in plan(row).solution_html


@pytest.mark.parametrize("group", ["508510", "508539"])
def test_saved_answer_parent_and_asset_guards(group):
    row = next(r for r in ROWS if r["group"] == group and r["task"] != group)
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    assert plan(row, ctx).answer == model(row).answer
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Чужой родитель.</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("x+3", "x+4"),
        ("x+3", "x^{2}+3"),
        ("+30", "-30"),
        ("x^{4}-2x^{3}+x^{2}", "x^{4}-2x^{3}+x^{2}+1"),
        (r"\ge", r"\ge 1+"),
        (r"\lg", r"\ln"),
        ("x^{2}-x+30", r"\frac{x-4}{x-4}(x^{2}-x+30)"),
    ],
)
def test_quotient_rejects_mismatched_bases_extra_terms_hidden_poles_and_wrong_substitution(
    old, new
):
    formula = read_formula(next(r["context"] for r in ROWS if r["task"] == "508510"))[1]
    assert old in formula
    with pytest.raises(UnsupportedCondition):
        quotient_comparison(formula.replace(old, new, 1))


@pytest.mark.parametrize(
    "old,new",
    [
        (r"\log_x", r"\log_{2x}"),
        ("x^{3}-8", "x^{3}-2"),
        ("x^{3}-8", "x^{3}+1"),
        (r"\le", r"\ge"),
        ("2x-13", "2x^{2}-13"),
        ("2x-13", "2x-13)+0("),
    ],
)
def test_cubic_rejects_incomplete_arguments_other_bases_non_cube_thresholds_and_nonlinear_differences(
    old, new
):
    formula = read_formula(next(r["context"] for r in ROWS if r["task"] == "508539"))[1]
    assert old in formula
    with pytest.raises(UnsupportedCondition):
        cubic_comparison(formula.replace(old, new, 1))
