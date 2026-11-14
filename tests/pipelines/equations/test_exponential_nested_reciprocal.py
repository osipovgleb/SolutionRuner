"""Check both substitutions, signed reciprocal branches and missing source proofs."""

import json
import re
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
from solution_runner.pipelines.equations.exponential_nested_reciprocal import (
    analyze,
    y_cases,
)
from solution_runner.pipelines.equations.exponential_nested_reciprocal_proof import (
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_nested_reciprocal_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("513100").content_rule_key)


def plan(context, parent=PARENT):
    return handler().plan(PlanInput(context, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_every_actual_answer_exact_substitutions_and_independent_cas(row):
    a = analyze(read_formula(row["context"])[1])
    A, B, C = a.coefficients
    assert sp.cancel(a.original_power - (A / (X - 1) ** 2 + B / (X - 1) + C)) == 0
    assert sp.cancel(a.stage.original.subs(X, 1 / (X - 1)) - a.original_power) == 0
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original_power, 0), X, relational=False
    ).intersect(sp.Interval.open(0, sp.oo))
    same_set(independent, a.power_solution)
    same_set(a.solution, answer_set(row["source_answer"]))
    assert a.y_solution.contains(-sp.Rational(1, 2)) is sp.true
    assert a.y_solution.contains(0) is sp.false
    assert a.power_solution.contains(1) is sp.false
    assert a.solution.contains(0) is sp.true
    assert (
        a.solution.intersect(sp.solveset(a.exponent, X, domain=sp.S.Reals))
        == sp.EmptySet
    )
    assert sp.Union(*(b.solution for b in a.branches)) == a.solution
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_method_variable_roles_and_branch_order(row):
    a = analyze(read_formula(row["context"])[1])
    html = render(a)
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").find_all(
            attrs={"data-inline-latex": True}
        )
    ]
    assert formulas[0].startswith("y=") and r"y\ne0" in formulas[0]
    assert r"t=\frac{1}{y}" in formulas and r"\frac{1}{y}" in formulas[5]
    assert all(not re.search(r"(?<![a-zA-Z])t(?![a-zA-Z])", f) for f in formulas[8:])
    assert y_cases(a.inverse_branches)[0] == sp.Interval.open(-sp.oo, 0)
    assert a.branches[0].values == sp.Interval.open(0, 1)
    assert isinstance(a.branches[1].values, sp.FiniteSet)
    assert isinstance(a.branches[2].values, sp.Interval)
    assert "<img " not in html and "x=0" in html
    assert "может быть как положительной, так и отрицательной" in html


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_missing_solutions_immutable_condition_and_replay(row):
    context = deepcopy(row["context"])
    original = deepcopy(context)
    p = plan(context)
    assert context == original and not handler().diagram_specs(context)
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(context)
    result = _prepared_record(
        gateway,
        {"problem_id": context["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert result["status"] == "prepared" and result["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [context["problem_id"]]
    replay(context, p.transformations)
    assert not plan(context).transformations
    if row["task"] in ("679622", "679631"):
        assert not any(
            s["key"] == "solution" for s in original["normalized_content"]["sections"]
        )
        assert any(
            s["key"] == "solution" for s in context["normalized_content"]["sections"]
        )


@pytest.mark.parametrize(
    "operator,expected",
    [
        (
            ">",
            sp.Union(
                sp.Interval.open(-sp.oo, -sp.sqrt(2)),
                sp.Interval.open(-sp.sqrt(2), -1),
                sp.Interval.open(1, sp.sqrt(2)),
                sp.Interval.open(sp.sqrt(2), sp.oo),
            ),
        ),
        ("<", sp.Union(sp.Interval.open(-1, 0), sp.Interval.open(0, 1))),
        (r"\le", sp.Interval(-1, 1)),
    ],
)
def test_strict_and_reversed_relations_preserve_boundary_membership(operator, expected):
    a = analyze(r"\frac{3}{(2^{2-x^2}-1)^2}-\frac{4}{2^{2-x^2}-1}+1" + operator + "0")
    same_set(a.solution, expected)


def test_shifted_quadratic_vertex_and_zero_constant_are_computed():
    original = analyze(r"\frac{3}{(2^{2-x^2}-1)^2}-\frac{4}{2^{2-x^2}-1}+1\ge0")
    shifted = analyze(r"\frac{3}{(2^{2-(x-1)^2}-1)^2}-\frac{4}{2^{2-(x-1)^2}-1}+1\ge0")
    for x in (-3, -2, -1, 0, 1, 2, 3):
        assert shifted.solution.contains(x + 1) == original.solution.contains(x)
    zero = analyze(r"\frac{3}{(2^{2-x^2}-1)^2}-\frac{4}{2^{2-x^2}-1}\ge0")
    assert zero.coefficients[-1] == 0
    assert zero.power_solution.contains(1) is sp.false


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{3}{(2^x-1)^2}-\frac{4}{2^x-1}+1\ge0",
        r"\frac{3}{(2^{2-x^2}-2)^2}-\frac{4}{2^{2-x^2}-2}+1\ge0",
        r"\frac{3}{(2^{2-x^2}-1)^3}-\frac{4}{2^{2-x^2}-1}+1\ge0",
        r"\frac{3}{(2^{2-x^2}-1)^2}-\frac{4}{2^{2-x^2}-1}+x\ge0",
    ],
)
def test_other_domains_degrees_or_ordinary_x_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_unknown_parent_or_assets_fail_closed_and_answers_do_not_drive_math():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "wrong")
    ctx["normalized_content"]["assets"] = [{"asset_id": "unknown"}]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
    ctx = deepcopy(ROWS[0]["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == plan(ROWS[0]["context"]).answer
