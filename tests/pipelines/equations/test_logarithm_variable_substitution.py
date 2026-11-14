"""Variable-base holes before cancellation and both source substitution methods."""

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
from solution_runner.pipelines.equations.logarithm_variable_substitution import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_variable_substitution_sources.json")
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
MANUAL = {
    "507635": ((X + 1) * (X - 3) / (3 * (X - 1)) - 1, "<=", (1, 3)),
    "507646": ((X + 3) * (X - 1) / (4 * (X - 3)) - sp.Rational(1, 4), "<=", (1, 3)),
    "511459": ((X + 3) * (X - 2) / (4 * (X - 3)) - sp.Rational(1, 4), "<=", (2, 3)),
    "508502": (-2 / (X + 1) - X - 4, "<=", (-1,)),
    "508504": (-2 / (X + 1) - X - 4, ">=", (-1,)),
    "511556": (-1 / (X + 1) - X - 3, ">=", (-1,)),
}
PARAMETERS = {
    "507635": (2, sp.Rational(1, 2), sp.Rational(1, 8), 8, 1),
    "507646": (8, sp.Rational(1, 8), sp.Rational(1, 2), 16, sp.Rational(1, 4)),
    "511459": (8, sp.Rational(1, 8), sp.Rational(1, 4), 16, sp.Rational(1, 4)),
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
    return analyze(read_formula(row["context"])[1])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_manual_answers_original_poles_and_independent_cas(row):
    a = model(row)
    expr, operator, holes = MANUAL[row["task"]]
    assert (
        sp.cancel(a.stage.original - expr) == 0
        and a.stage.operator == operator
        and set(a.stage.poles) == set(holes)
    )
    oracle = sp.solve_univariate_inequality(
        {"<=": sp.Le, ">=": sp.Ge}[operator](expr, 0), X, relational=False
    ) - sp.FiniteSet(*holes)
    same_set(a.stage.solution, oracle)
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert plan(row).answer == a.answer
    for level in holes:
        assert (
            a.domain.contains(2 ** sp.Integer(level)) is sp.false
            and a.solution.contains(2 ** sp.Integer(level)) is sp.false
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_values_and_each_change_of_base_identity(row):
    a = model(row)
    _, operator, holes = MANUAL[row["task"]]
    for i in range(-30, 31):
        t = sp.Rational(i, 5)
        if t in holes:
            continue
        x = 2 ** float(t)
        if row["task"] in PARAMETERS:
            u, v, w, d, bound = PARAMETERS[row["task"]]
            value = math.log2(float(u) * x) * math.log(2, float(v) * x) / math.log(
                float(d), float(w) * x
            ) - float(bound)
        else:
            arg = 0.5 if row["task"] == "511556" else 0.25
            coefficient = 16 if row["task"] == "511556" else 32
            value = math.log(arg, 2 * x) - math.log2(coefficient * x) + 1
        expected = value <= 1e-9 if operator == "<=" else value >= -1e-9
        assert bool(a.solution.contains(sp.Integer(2) ** t)) == expected, (
            row["task"],
            t,
        )
        for term in a.terms:
            actual = math.log(
                float(term.argument.subs(X, x)), float(term.base.subs(X, x))
            )
            assert (
                abs(actual - float((term.numerator / term.denominator).subs(X, t)))
                < 1e-8
            )
    for x in (-1, 0):
        assert a.domain.contains(x) is sp.false


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replays_exactly_without_assets_or_condition_writes(row):
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


@pytest.mark.parametrize("task,hole", [("507635", 3), ("507646", 1), ("511459", 2)])
def test_outer_quotient_cancellation_retains_original_base_hole_and_parent_order(
    task, hole
):
    row = next(r for r in ROWS if r["task"] == task)
    a = model(row)
    assert (
        hole in a.stage.holes and a.solution.contains(sp.Integer(2) ** hole) is sp.false
    )
    formulas = [
        v["data-inline-latex"]
        for v in BeautifulSoup(plan(row).solution_html, "html.parser").select(
            "[data-inline-latex]"
        )
    ]
    definition = next(i for i, f in enumerate(formulas) if f.startswith("y="))
    assert definition > next(
        i for i, f in enumerate(formulas) if "=" in f and r"\log_" in f
    )
    last_exclusion = next(
        i
        for i, f in enumerate(formulas)
        if i > definition and f == "x\\ne" + sp.latex(sp.Integer(2) ** hole)
    )
    assert last_exclusion < len(formulas) - 1


def test_irrational_levels_remain_inside_exponents_and_double_zero_does_not_make_a_hole():
    row = next(r for r in ROWS if r["task"] == "511459")
    a = model(row)
    assert {-sp.sqrt(3), sp.sqrt(3)} <= set(a.stage.zeros)
    assert "2^{- \\sqrt{3}}" in a.answer and "2^{\\sqrt{3}}" in a.answer
    for level in (-sp.sqrt(3), sp.sqrt(3)):
        assert a.solution.contains(2**level) is sp.true
    row = next(r for r in ROWS if r["task"] == "511556")
    a = model(row)
    assert a.solution.contains(sp.Rational(1, 4)) is sp.true
    assert "z=" in plan(row).solution_html and "y=" not in plan(row).solution_html


@pytest.mark.parametrize("group", ["507635", "508502"])
def test_saved_answer_parent_and_asset_guards(group):
    row = next(r for r in ROWS if r["group"] == group and r["task"] != group)
    ctx = deepcopy(row["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] == "answer":
            s["html"] = "<p>999</p>"
    assert plan(row, ctx).answer == model(row).answer
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Чужой родитель.</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{2x}0.25\le\log_3(32x)-1",
        r"\log_{x+1}0.25\le\log_2(32x)-1",
        r"\log_{x^2}0.25\le\log_2(32x)-1",
        r"\log_{(-2x)}0.25\le\log_2(32x)-1",
        r"\log_{2x}0.25\le\log_2(32x)-x",
        r"\log_{2x}0.25\le\log_2(32y)-1",
        r"\log_{2x}0.25\le\log_2(32x)^{2}-1",
        r"\log_{2x}0.25\le\log_2(\frac{x-1}{x-1}32x)-1",
        r"\log_{2x}0.25\le\log_2(3x)-1",
        r"\log_{2x}0.25\le\log_{10000}(32x)-1",
        r"\log_{2x}0.25\le\log_{\frac{1}{2}}(32x)-1",
        r"\log_2(2x)\le1",
        r"\log_{2x}0.25\le\log_{3x}32-1",
    ],
)
def test_incomplete_or_unreviewed_bases_arguments_outside_variables_and_powers_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_displayed_substitution_replaces_both_sides_and_keeps_reciprocal_first(row):
    formulas = [
        v["data-inline-latex"]
        for v in BeautifulSoup(plan(row).solution_html, "html.parser").select(
            "[data-inline-latex]"
        )
    ]
    name = "y" if row["group"] == "507635" else "z"
    definition = next(i for i, f in enumerate(formulas) if f.startswith(name + "="))
    assert name in formulas[definition + 1] and "x" not in formulas[definition + 1]
    assert not any(r"\lex" in f or r"\gex" in f for f in formulas)
    if row["group"] == "508502":
        reciprocal = next(i for i, f in enumerate(formulas) if r"=\frac{1}{\log_" in f)
        general = next(i for i, f in enumerate(formulas) if r"=\frac{\log_" in f)
        assert reciprocal < general < definition


def test_numeric_fixed_log_argument_does_not_gain_a_spurious_variable():
    row = next(r for r in ROWS if r["task"] == "508502")
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "condition":
            section["html"] = (
                r'<p>Решите неравенство: <span data-inline-latex="\log_{2x}0.25\le\log_2(8)-1"></span></p>'
            )
    p = plan(row, ctx)
    assert r"\log_2(8)=3" in p.solution_html
    assert r"\log_2(8)=\log_" not in p.solution_html
