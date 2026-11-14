"""Certify reciprocal-sum range, inverse intervals and read-only parent preparation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_reciprocal_sum import (
    analyze,
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_reciprocal_sum_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("508319").content_rule_key)


def plan(context, parent=PARENT):
    return handler().plan(PlanInput(context, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_source_answers_identities_range_and_independent_positive_cas(row):
    a = analyze(read_formula(row["context"])[1])
    coefficients = dict(a.coefficients)
    u = sp.Symbol("u", positive=True)
    original = sum(c * u**k for k, c in a.coefficients)
    quadratic = a.stage.original.subs(X, u + 1 / u)
    assert sp.cancel(original - quadratic) == 0
    independent = sp.solve_univariate_inequality(original <= 0, u, relational=False)
    assert sp.Intersection(independent, sp.Interval.open(0, sp.oo)) == sp.FiniteSet(1)
    assert a.reachable == sp.FiniteSet(2) and a.positive == sp.FiniteSet(1)
    assert a.solution == sp.FiniteSet(0)
    assert coefficients[2] == coefficients[-2] == 1
    html = render(a)
    assert r"t\ge 2" in html and "t=2" in html and "x=0" in html
    assert "t^{^{2}}" not in html and "<img " not in html
    assert plan(row["context"]).answer == r"\{0\}"


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replay_and_condition_immutability(row):
    context = deepcopy(row["context"])
    original = deepcopy(context)
    p = plan(context)
    assert context == original
    assert not handler().diagram_specs(context)
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


@pytest.mark.parametrize(
    "operator,expected",
    [
        (r"\le", sp.Interval(-1, 1)),
        ("<", sp.Interval.open(-1, 1)),
        (r"\ge", sp.Union(sp.Interval(-sp.oo, -1), sp.Interval(1, sp.oo))),
        (">", sp.Union(sp.Interval.open(-sp.oo, -1), sp.Interval.open(1, sp.oo))),
    ],
)
def test_larger_reciprocal_sum_range_preserves_interval_endpoints(operator, expected):
    a = analyze(
        r"4^x+\frac{1}{4^x}+3\cdot2^x+\frac{3}{2^x}" + operator + r"\frac{47}{4}"
    )
    assert a.solution == expected
    assert "исходной переменной" in render(a)


@pytest.mark.parametrize("bound,expected", [("7", sp.EmptySet), ("8", sp.FiniteSet(0))])
def test_unreachable_range_and_singleton_are_derived(bound, expected):
    a = analyze(r"9^x+\frac{1}{9^x}+3^{x+1}+3^{1-x}\le " + bound)
    assert a.solution == expected


def test_negative_coefficients_and_scaled_affine_exponents():
    a = analyze(
        r"-4^{2x}-\frac{1}{4^{2x}}-3\cdot2^{2x}-\frac{3}{2^{2x}}\ge-\frac{47}{4}"
    )
    assert a.solution == sp.Interval(-sp.Rational(1, 2), sp.Rational(1, 2))


@pytest.mark.parametrize(
    "formula",
    [
        r"4^x+\frac{2}{4^x}+3\cdot2^x+\frac{3}{2^x}\le8",
        r"4^x+\frac{1}{4^x}+3\cdot2^x+\frac{4}{2^x}\le8",
        r"2^x+\frac{1}{2^x}\le2",
    ],
)
def test_asymmetric_or_missing_square_pair_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_parent_source_assets_and_unknown_answers_are_handled_safely():
    context = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(context, PARENT + "wrong")
    context["normalized_content"]["assets"] = [{"asset_id": "unknown"}]
    with pytest.raises(UnsupportedCondition):
        plan(context)
    context = deepcopy(ROWS[0]["context"])
    for s in context["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>wrong</p>"
    assert plan(context).answer == r"\{0\}"
