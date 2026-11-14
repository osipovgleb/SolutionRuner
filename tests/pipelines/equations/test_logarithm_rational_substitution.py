"""Check all source rational substitutions, original exclusions and inverse endpoints."""

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
from solution_runner.pipelines.equations.logarithm_rational_substitution import (
    analyze,
    inverse,
)
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_rational_substitution_sources.json")
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
    "517447": ((X + 3) / (X - 3) + (X - 3) / (X + 3) - (4 * X + 16) / (X**2 - 9), ">="),
    "517440": (
        (X + 4) / (X - 4) + (X - 4) / (X + 4) - (24 - 8 * X) / (X**2 - 16),
        ">=",
    ),
    "517454": ((X + 2) / (X - 2) + (X - 2) / (X + 2) - (6 - 4 * X) / (X**2 - 4), ">="),
    "643171": (
        (X + 5) / (X - 5) + (X - 5) / (X + 5) - (16 * X + 18) / (X**2 - 25),
        ">=",
    ),
    "517547": ((4 * X + 13) / (X**2 - 9) + 1, ">="),
    "517559": ((2 * X - 5) / (X**2 - 4) - 1, "<="),
    "517819": ((X + 2) ** 2 / (X**2 - 9), ">="),
    "517816": ((X - 11) / (X**2 + 4 * X) - 1, "<="),
    "548182": ((X - 11) / (X**2 + 4 * X) - 1, "<="),
    "517817": ((X + 1) / (X**2 + 3 * X) + 1, ">="),
    "517818": ((X + 1) / (X**2 - 3 * X), ">="),
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
def test_manual_source_answers_rewritten_expressions_and_independent_cas(row):
    a = model(row)
    manual, operator = MANUAL[row["task"]]
    assert sp.cancel(a.stage.original - manual) == 0 and a.stage.operator == operator
    relation = {">=": sp.Ge, "<=": sp.Le}[operator]
    oracle = sp.solve_univariate_inequality(
        relation(manual, 0), X, relational=False
    ) - sp.FiniteSet(*a.stage.poles)
    same_set(a.stage.solution, oracle)
    if row["task"] == "517817":
        expected = sp.Union(
            sp.Interval.Lopen(0, 4 ** (-2 - sp.sqrt(3))),
            sp.Interval.Lopen(sp.Rational(1, 64), 4 ** (-2 + sp.sqrt(3))),
            sp.Interval.open(1, sp.oo),
        )
    else:
        expected = answer_set(row["expected_answer"])
    same_set(a.solution, expected)
    assert a.answer.replace(" ", "") == row["expected_answer"].replace(
        "+\\infty", "\\infty"
    ).replace(" ", "")
    assert plan(row).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_values_and_excluded_denominators(row):
    a = model(row)
    manual, operator = MANUAL[row["task"]]
    for level in (-6, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5):
        x = a.base**level
        if level in a.stage.poles:
            assert (
                a.domain.contains(x) is sp.false and a.solution.contains(x) is sp.false
            )
            continue
        value = sp.cancel(manual.subs(X, level))
        expected = value >= 0 if operator == ">=" else value <= 0
        assert bool(a.solution.contains(x)) == bool(expected)
        for term in a.terms:
            original = (
                sp.log(term.coefficient * x**term.degree) / sp.log(a.base)
            ) ** term.power
            reduced = term.linear.subs(X, level) ** term.power
            assert sp.simplify(sp.expand_log(original) - reduced) == 0
    for x in (-3, -1, 0):
        assert a.domain.contains(x) is sp.false and a.solution.contains(x) is sp.false


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_has_no_assets_writes_and_replays_exactly(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original
    assert (
        not handler(row).diagram_specs(ctx) and not ctx["normalized_content"]["assets"]
    )
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


@pytest.mark.parametrize(
    "task,level",
    [
        ("517447", 1),
        ("517440", -2),
        ("517454", -1),
        ("643171", 4),
        ("517547", -2),
        ("517559", 1),
        ("517819", -2),
    ],
)
def test_isolated_points_survive_and_remain_between_the_two_open_intervals(task, level):
    row = next(r for r in ROWS if r["task"] == task)
    a = model(row)
    point = a.base**level
    assert a.solution.contains(point) is sp.true
    for nearby in (level - sp.Rational(1, 100), level + sp.Rational(1, 100)):
        assert a.solution.contains(a.base**nearby) is sp.false
    assert [part.inf for part, _ in a.images] == [
        -sp.oo,
        sp.Integer(level),
        max(a.stage.poles),
    ]
    html = plan(row).solution_html
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    choices = next(f for f in formulas if r"\begin{aligned}t" in f)
    assert (
        choices.index("t<")
        < choices.index("t=" + sp.latex(level))
        < choices.index(r"t\gt")
    )


def test_original_cancelled_log_denominator_is_retained_before_simplification():
    formula = (
        r"\frac{\log_4(16x^{4})+11}{\log_4^{2}x-9}\ge-1+\frac{\log_4x-4}{\log_4x-4}-1"
    )
    a = analyze(formula)
    baseline = model(next(r for r in ROWS if r["task"] == "517547"))
    assert (
        sp.cancel(a.stage.original - baseline.stage.original) == 0
        and 4 in a.stage.poles
    )
    same_set(a.solution, baseline.solution - sp.FiniteSet(256))
    assert a.domain.contains(256) is sp.false


def test_irrational_levels_stay_inside_the_exponent_and_do_not_widen_old_arithmetic():
    row = next(r for r in ROWS if r["task"] == "517817")
    a = model(row)
    assert set(a.stage.zeros) == {-2 - sp.sqrt(3), -2 + sp.sqrt(3)}
    assert r"4^{-2 - \sqrt{3}}" in a.answer and r"4^{-2 + \sqrt{3}}" in a.answer
    assert (
        4 ** (-2) - sp.sqrt(3) < 0
        and a.solution.contains(sp.Rational(1, 4096)) is sp.true
    )
    with pytest.raises(UnsupportedCondition):
        ScalarParser(r"4^{-2+\sqrt{3}}").parse()
    assert "4^{-2 - \\sqrt{3}}" in plan(row).solution_html


def test_substitution_first_and_algebra_first_parent_order_and_already_factored_child():
    for group, substitution_first in [
        ("517447", True),
        ("517547", False),
        ("517816", False),
    ]:
        row = next(r for r in ROWS if r["task"] == group)
        html = plan(row).solution_html
        formulas = [
            s["data-inline-latex"]
            for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
        ]
        definition = next(i for i, f in enumerate(formulas) if f.startswith("t="))
        identity = next(
            i for i, f in enumerate(formulas) if f.startswith(r"\log_") and "=" in f
        )
        assert (definition < identity) == substitution_first
    row = next(r for r in ROWS if r["task"] == "517819")
    assert "Приведём слагаемые" not in plan(row).solution_html


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{\log_2x}{\log_3x-1}\ge1",
        r"\frac{\log_4(16x^4)+11}{\log_4^2x-9}\ge-1+\frac{x}{x}-1",
        r"\frac{\log_4(\frac{x-2}{x-2}x)+11}{\log_4^2x-9}\ge-1",
        r"\frac{\log_4x^{21}+11}{\log_4^2x-9}\ge-1",
        r"\frac{\log_4x^{2}+11}{\log_4^2x^{2}-9}\ge-1",
        r"\frac{\log_4(-x)+11}{\log_4^2x-9}\ge-1",
        r"\frac{\log_x x+11}{\log_x^2x-9}\ge-1",
        r"\frac{\log_2(3x)+11}{\log_2^2x-9}\ge-1",
        r"\frac{(\log_2x+1)^4}{(\log_2x-3)^4}\ge1",
    ],
)
def test_unreviewed_bases_original_poles_powers_coefficients_and_even_domains_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize("level", [sp.Integer(31), sp.real_root(2, 3), sp.log(2)])
def test_inverse_levels_are_bounded_and_quadratic(level):
    with pytest.raises(UnsupportedCondition):
        inverse(sp.Integer(4), level)


@pytest.mark.parametrize("group", ["517447", "517547", "517816"])
def test_parent_saved_answer_and_unreviewed_assets_are_independent_guards(group):
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
