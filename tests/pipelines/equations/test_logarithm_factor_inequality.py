"""Validate complete factor-log groups, original domains and all parent methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_logarithmic_input import read_equation
from solution_runner.pipelines.equations.logarithm_factor_arguments import read_argument
from solution_runner.pipelines.equations.logarithm_factor_figures import SOURCES
from solution_runner.pipelines.equations.logarithm_factor_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_factor_inequality_sources.json")
    .read_text()
)
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["group"] == r["task"]
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, ctx=None, parent=None):
    ctx = row["context"] if ctx is None else ctx
    return handler(row).plan(
        PlanInput(
            _with_required_assets(ctx, handler(row).key),
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_every_complete_source_answer_and_independent_cas_domain(row):
    a = analyze(read_formula(row["context"])[1])
    same_set(a.solution, answer_set(row["expected_answer"]))
    oracle = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg.value > 0, X, relational=False)
            - sp.FiniteSet(*arg.excluded)
            for arg in a.arguments
        )
    )
    same_set(a.domain, oracle)
    same_set(answer_set(plan(row).answer), a.solution)
    for arg in a.arguments:
        reconstructed = arg.coefficient * sp.prod(f**k for f, k in arg.factors)
        assert sp.cancel(reconstructed - arg.value) == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_values_match_reduction_on_valid_and_invalid_samples(row):
    a = analyze(read_formula(row["context"])[1])
    for point in (-15, -9, -6, -3, -1, 0, sp.Rational(3, 2), 2, 4, 6, 10, 18):
        if a.domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        args = [arg.value.subs(X, point) for arg in a.arguments]
        original = (
            sum(
                c * sp.log(v) / sp.log(atom.base)
                for c, v, atom in zip(a.coefficients, args, a.atoms, strict=True)
            )
            + a.constant
        )
        residual = (
            a.multiplier * sp.log(abs(a.reduced.subs(X, point))) / sp.log(a.base)
            + sp.log(a.scalar) / sp.log(a.base)
            + a.constant
        )
        assert abs(float(sp.N(original - residual, 50))) < 1e-35
        original = sp.simplify(sp.expand_log(original))
        sign = sp.N(original, 50)
        expected = {"<": sign < 0, "<=": sign <= 0, ">": sign > 0, ">=": sign >= 0}[
            a.operator
        ]
        assert bool(a.solution.contains(point)) == bool(expected)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replay_conditions_assets_and_all_parent_ways(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before and not handler(row).diagram_specs(ctx)
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
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
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    if row["group"] == "642420":
        positions = [
            p.solution_html.index(t)
            for t in ("Первый способ", "Другой способ", "Ещё один способ")
        ]
        assert positions == sorted(positions)
        assert "положительная" in p.solution_html.lower()
    replay(ctx, p.transformations)
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert not plan(row, ctx).transformations


def test_high_power_negative_branch_and_rational_quartic_are_not_dropped():
    outlier = next(r for r in ROWS if r["task"] == "484594")
    a = analyze(read_formula(outlier["context"])[1])
    same_set(a.solution, sp.Union(sp.Interval.Ropen(-15, -6), sp.Interval.Lopen(-5, 5)))
    assert (
        a.solution.contains(-10) is sp.true and r"\left|" in plan(outlier).solution_html
    )
    quartic = next(r for r in ROWS if r["task"] == "507708")
    a = analyze(read_formula(quartic["context"])[1])
    assert sp.degree(sp.fraction(a.stage.expression)[0], X) == 4
    assert "положителен" in plan(quartic).solution_html


def test_argument_power_optin_keeps_old_logarithmic_reader_semantics():
    formula = r"\log_2(x-3)^4=\log_2(x+1)"
    atoms, old = read_equation(formula, extended=True)
    assert (
        atoms[0].argument == X - 3
        and sp.Poly(old, *[a.symbol for a in atoms]).total_degree() == 4
    )
    atoms, new = read_equation(formula, extended=True, argument_powers=True)
    assert (
        atoms[0].argument == sp.expand((X - 3) ** 4)
        and sp.Poly(new, *[a.symbol for a in atoms]).total_degree() == 1
    )


def test_original_even_zeros_denominators_and_cancelled_holes_survive_factorization():
    a = read_argument(r"\frac{(x-2)^2}{(x-2)^2(x+3)}")
    same_set(a.domain, sp.Interval.open(-3, sp.oo) - sp.FiniteSet(2))
    assert a.value == 1 / (X + 3) and a.excluded == (-3, 2)
    same_set(read_argument("x/x").domain, sp.S.Reals - sp.FiniteSet(0))
    formula = r"\log_2(\frac{x(x+4)(x-2)}{x-2})+\log_{(0{,}5)}\frac{x}{4}+2\ge\log_2(x^2+3x-4)"
    same_set(analyze(formula).solution, sp.Interval.Lopen(1, 17) - sp.FiniteSet(2))


@pytest.mark.parametrize("task", ["507708", "508466"])
def test_exact_compatible_original_chart_is_reused_and_missing_chart_is_shared(task):
    row = next(r for r in ROWS if r["task"] == task)
    ctx = deepcopy(row["context"])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    assert uid in plan(row, ctx).solution_html
    ctx["normalized_content"]["assets"] = []
    assert uid in plan(row, ctx).solution_html
    assert not handler(row).diagram_specs(ctx)


@pytest.mark.parametrize("task", ["507708", "508466"])
def test_matching_final_answer_does_not_allow_wrong_plot_signature(task, monkeypatch):
    row = next(r for r in ROWS if r["task"] == task)
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    monkeypatch.setitem(SOURCES["figures"][uid], "domain", "foreign")
    with pytest.raises(UnsupportedCondition):
        plan(row)


def test_decorative_icons_stay_unchanged_and_are_not_math_diagrams():
    row = next(r for r in ROWS if r["task"] == "642792")
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    assert "<img " not in plan(row, ctx).solution_html and ctx == before
    ctx["normalized_content"]["assets"][0]["url"] = "/assets/foreign"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2(x+1)+x\le\log_2(x-1)",
        r"\log_2^2(x+1)\le\log_2(x-1)",
        r"\log_2(x+1)\le\log_3(x-1)",
        r"100\log_2(x+1)\le\log_2(x-1)",
        r"\log_2(x+1)\le\log_2(x-1)^21",
        r"\log_2(x+y)\le\log_2(x-1)",
        r"\log_2(0)\le\log_2(x-1)",
        r"\log_x(x+1)\le\log_x(x-1)",
    ],
)
def test_unreviewed_factor_grammar_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_parent_asset_guards_and_original_answer_independence():
    for key, parent in PARENTS.items():
        row = next(r for r in ROWS if r["group"] == key)
        ctx = deepcopy(row["context"])
        expected = plan(row, ctx).answer
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx, parent + "changed")
        for s in ctx["normalized_content"]["sections"]:
            if s["key"] in ("answer", "solution"):
                s["html"] = "<p>wrong</p>"
        assert plan(row, ctx).answer == expected
        ctx["normalized_content"]["assets"] = [{"asset_id": "foreign"}]
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx)
