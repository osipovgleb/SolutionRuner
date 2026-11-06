"""Quadratic exponent ranges, logarithmic roots, isolated points and native proofs."""

import json
import re
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_quadratic import answer_set as interval_set
from test_exponential_inequality_quadratic import endpoint, same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import back_substitute
from solution_runner.pipelines.equations.exam_scalar import (
    compare,
    enclose,
    log_rational,
)
from solution_runner.pipelines.equations.exponential_inequality_preimages import (
    analyze,
    branch,
    power_range,
)
from solution_runner.pipelines.equations.exponential_inequality_quadratic import (
    analyze_quadratic,
)
from solution_runner.pipelines.equations.logarithm_arithmetic import actual
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X, polynomial
from solution_runner.pipelines.equations.rational_inequality_roots import (
    ordered,
    quadratic_roots,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_preimage_sources.json")
    .read_text()
)


def answer_set(text):
    sets = []
    for part in text.strip().removesuffix(".").strip().split(r"\cup"):
        part = part.strip()
        sets.append(
            sp.FiniteSet(*(endpoint(t) for t in part[2:-2].split(";")))
            if part.startswith(r"\{")
            else interval_set(part)
        )
    return sp.Union(*sets)


def parent(row):
    p = next(r for r in SOURCES if r["task"] == row["group"])
    return next(
        s["html"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def rule(row):
    return get_group_profile(row["group"]).content_rule_key


def plan(row, ctx=None):
    return get_handler(rule(row)).plan(
        PlanInput(ctx or row["context"], parent_solution_html=parent(row))
    )


def analysis(row):
    return analyze(read_formula(row["context"])[1])


def exact_zero(value):
    assert sp.simplify(sp.expand_log(sp.expand(value.rewrite(sp.exp)), force=True)) == 0


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_identity_source_answer_and_independent_cas_of_every_branch(row):
    a = analysis(row)
    actual_power = a.base**a.exponent
    assert actual_power.is_positive is True
    exact_zero(
        a.original * actual_power**a.multiply_degree
        - a.stage.original.subs(X, actual_power)
    )
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}
    oracle = sp.solve_univariate_inequality(
        relation[a.operator](a.stage.original, 0), X, relational=False
    )
    assert a.positive_solution == oracle.intersect(sp.Interval.open(0, sp.oo))
    for b in a.branches + a.reachable_branches:
        parts = []
        for c in b.conditions:
            independent = (
                sp.solveset(a.exponent - c.value, X, domain=sp.S.Reals)
                if c.operator == "="
                else sp.solve_univariate_inequality(
                    relation[c.operator](a.exponent, c.value), X, relational=False
                )
            )
            same_set(c.solution, independent)
            for r in c.points:
                exact_zero(a.exponent.subs(X, r) - c.value)
            parts.append(independent)
        oracle = (
            sp.Union(*parts)
            if isinstance(b.values, sp.FiniteSet)
            else sp.Intersection(*parts)
        )
        same_set(b.solution, oracle)
    same_set(a.solution, sp.Union(*(b.solution for b in a.reachable_branches)))
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(a.solution, answer_set(a.answer))
    same_set(a.solution, answer_set(plan(row).answer))


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_vertex_range_is_attained_and_labels_are_exact_closed_logarithms(row):
    a = analysis(row)
    p = sp.Poly(a.exponent, X)
    vertex = -p.nth(1) / (2 * p.nth(2))
    value = p.eval(vertex)
    exact_zero(a.exponent - (p.nth(2) * (X - vertex) ** 2 + value))
    limit = a.base**value
    assert limit in a.power_range and 0 not in a.power_range
    assert a.power_range.start == limit if p.LC() > 0 else a.power_range.end == limit
    for _, _, roots in a.back:
        for root in roots:
            label = a.endpoint(root)
            exact_zero(actual(LogarithmParser(label).parse().value) - root)
    if row["group"] == "508509":
        assert a.power_range == sp.Interval(1, sp.oo) and 0 in a.solution
        assert a.answer.index(r"\{0\}") > a.answer.index(r"-\infty")
    if row["task"] == "517740":
        assert (
            a.power_range == sp.Interval.Lopen(0, 27)
            and sp.FiniteSet(2) in a.solution.args
        )
    if row["task"] == "518115":
        assert a.exponent == X**2 + 2 * X - 5 and a.power_range == sp.Interval(
            sp.Rational(1, 64), sp.oo
        )
        assert len(a.solution.args) == 3 and r"\cup" not in row["source_answer"]


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_readonly_gateway_replay_preserves_condition_and_has_no_assets(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    handler = get_handler(rule(row))
    assert (
        ctx == row["context"]
        and not handler.diagram_specs(ctx)
        and not handler.asset_requirements(ctx)
    )
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        rule(row),
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and not record.get("generated_diagrams")
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_parent_range_system_or_separate_branches_and_isolated_point(row):
    a = analysis(row)
    p = plan(row)
    lines = [
        s["data-inline-latex"]
        for s in BeautifulSoup(p.solution_html, "html.parser").find_all(
            "span", attrs={"data-inline-latex": True}
        )
    ]
    assert any(f.startswith("t=") for f in lines)
    if row["group"] == "508509":
        assert any(r"\begin{cases}" in f and r"t\ge 1" in f for f in lines)
        assert any(f == "x=0" for f in lines) and "положительное t" in p.solution_html
        assert p.solution_html.index("Сделаем замену") < p.solution_html.index(
            "Умножим"
        )
    else:
        assert not any(r"\begin{cases}" in f for f in lines)
        assert p.solution_html.count("<p>При ") == 2
        assert "Ветви объединяем" in p.solution_html
        if row["task"] in ("517740", "517750"):
            vertex = -sp.Poly(a.exponent, X).nth(1) / (
                2 * sp.Poly(a.exponent, X).nth(2)
            )
            assert "x=" + sp.latex(vertex) in lines
        else:
            assert not any(re.match(r"x=\d+$", f) for f in lines)


@pytest.mark.parametrize(
    "formula,expected",
    [
        (
            r"2^{x^2}+9\cdot2^{1-x^2}>19",
            sp.Interval.open(-sp.oo, -sp.sqrt(sp.log(18) / sp.log(2)))
            | sp.Interval.open(sp.sqrt(sp.log(18) / sp.log(2)), sp.oo),
        ),
        (
            r"2^{x^2}+9\cdot2^{1-x^2}\le19",
            sp.Interval(
                -sp.sqrt(sp.log(18) / sp.log(2)), sp.sqrt(sp.log(18) / sp.log(2))
            ),
        ),
        (r"4^{(x-1)^2}-2\cdot2^{(x-1)^2}+1\le0", sp.FiniteSet(1)),
        (r"4^{x^2}-2\cdot2^{x^2}+1<0", sp.EmptySet),
        (r"4^{-x^2}-5\cdot2^{-x^2}+4\le0", sp.FiniteSet(0)),
        (
            r"4^{x^2+2x-3}-5\cdot2^{x^2+2x-3}+4\le0",
            sp.Interval(-1 - sp.sqrt(6), -3) | sp.Interval(1, -1 + sp.sqrt(6)),
        ),
    ],
)
def test_strictness_tangent_empty_bounded_band_and_negative_curvature(
    formula, expected
):
    same_set(analyze(formula).solution, expected)


@pytest.mark.parametrize(
    "formula",
    [
        r"2^{x^3}+2^{-x^3}\le3",
        r"4^{x^2+x}-3\cdot2^{x^2}+2\le0",
        r"4^{x^2}-3\cdot3^{x^2}+2\le0",
        r"\frac{4^{x^2}}{x-1}+2^{x^2}\le3",
        r"4^{\frac{x^2}{x-1}}+2^{x^2}\le3",
        r"4^{x^2+1000000000000}+2^{x^2}\le3",
        r"(-4)^{x^2}+2^{x^2}\le3",
        r"8^{x^2}+2^{x^2}\le3",
    ],
)
def test_unsupported_exponents_bases_poles_and_offsets_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_logarithmic_quadratic_roots_use_certified_shared_scalar_bounds():
    value = sp.log(18) / sp.log(2)
    roots = ordered(quadratic_roots(sp.Poly(X**2 - value, X)))
    assert len(roots) == 2 and compare(roots[0], 0) < 0 < compare(roots[1], 0)
    for root in roots:
        exact_zero(root**2 - value)
        lo, hi = enclose(root, 32)
        assert lo < hi
    lower, upper = enclose(sp.log(2) ** sp.Rational(-1, 2), 32)
    loglo, loghi = log_rational(Fraction(2), 64)
    assert lower > 0 and lower**2 * loghi <= 1 <= upper**2 * loglo
    with pytest.raises(UnsupportedCondition):
        back_substitute(sp.Integer(2), X**2, (sp.Integer(18),))
    assert (
        len(
            back_substitute(
                sp.Integer(2), X**2, (sp.Integer(18),), quadratic_logs=True
            )[0]
        )
        == 2
    )


@pytest.mark.parametrize("base", (sp.Integer(0), sp.Integer(-1)))
def test_reciprocal_square_root_cannot_cross_or_leave_the_real_domain(base):
    with pytest.raises(UnsupportedCondition):
        enclose(sp.Pow(base, sp.Rational(-1, 2), evaluate=False))


def test_old_polynomial_and_affine_method_guards_are_not_relaxed():
    with pytest.raises(UnsupportedCondition):
        polynomial(X**2 - sp.log(3))
    with pytest.raises(UnsupportedCondition):
        analyze_quadratic(r"4^{x^2}-3\cdot2^{x^2}+2\le0")
    assert branch(sp.Integer(2), X**2, sp.FiniteSet(1)).solution == sp.FiniteSet(0)
    assert branch(
        sp.Integer(2), X**2, sp.Interval.open(1, 4)
    ).solution == sp.Interval.open(-sp.sqrt(2), 0) | sp.Interval.open(0, sp.sqrt(2))
    with pytest.raises(UnsupportedCondition):
        power_range(sp.Integer(2), X**3)


@pytest.mark.parametrize("group", ("508509", "517740"))
@pytest.mark.parametrize(
    "change",
    ("answer", "solution", "asset", "instruction", "parent", "other_method_parent"),
)
def test_only_condition_computes_answer_and_parent_method_is_certified(group, change):
    row = next(r for r in SOURCES if r["task"] == group)
    ctx = deepcopy(row["context"])
    if change in ("answer", "solution"):
        next(s for s in ctx["normalized_content"]["sections"] if s["key"] == change)[
            "html"
        ] = "<p>Неверно</p>"
        assert plan(row, ctx).answer == plan(row).answer
        return
    if change == "asset":
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    elif change == "instruction":
        next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )["html"] += "<p>Укажите только целые решения.</p>"
    with pytest.raises(UnsupportedCondition):
        if change in ("parent", "other_method_parent"):
            html = (
                parent(row) + " "
                if change == "parent"
                else parent(next(r for r in SOURCES if r["group"] != group))
            )
            get_handler(rule(row)).plan(PlanInput(ctx, parent_solution_html=html))
        else:
            plan(row, ctx)
