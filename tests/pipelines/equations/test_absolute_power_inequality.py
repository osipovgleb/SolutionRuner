"""Positive reciprocal powers, signed rational exponents and original pole guards."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.absolute_power_inequality import (
    reciprocal,
    signed_exponent,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("absolute_power_sources.json")
    .read_text()
)
PARENTS = {
    r["method"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}
R = sp.Rational
MANUAL = {
    "508567": (
        R(2, 3) * X - R(2, 3),
        X - R(6, 5),
        sp.FiniteSet(-R(1, 2), R(6, 5), R(5, 2)),
    ),
    "508568": (2 * X - 6, X + 1, sp.FiniteSet(-1, R(5, 2), R(7, 2))),
    "511576": (2 * X - 5, X + 1, sp.FiniteSet(-1, 2, 3)),
    "560732": (
        5,
        (X**2 - 7 * sp.Abs(X) + 10) / (X - 3) ** 2,
        sp.Union(sp.Interval(-5, -2), sp.Interval.Ropen(2, 3), sp.Interval.Lopen(3, 5)),
    ),
    "548295": (
        4,
        (X**2 - 7 * sp.Abs(X) + 6) / (X - 5) ** 2,
        sp.Union(
            sp.Interval.open(-6, -1), sp.Interval.open(1, 5), sp.Interval.open(5, 6)
        ),
    ),
    "560781": (
        7,
        (X**2 - 7 * sp.Abs(X) + 6) / (X - 4) ** 2,
        sp.Union(sp.Interval(-6, -1), sp.Interval.Ropen(1, 4), sp.Interval.Lopen(4, 6)),
    ),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, context=None, parent=None):
    return handler(row).plan(
        PlanInput(
            row["context"] if context is None else context,
            parent_solution_html=PARENTS[row["method"]] if parent is None else parent,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_six_independent_answers_domains_and_original_expressions(row):
    formula = read_formula(row["context"])[1]
    P, E, expected = MANUAL[row["task"]]
    if row["method"] == "reciprocal":
        a = reciprocal(formula)
        assert a.argument == P and a.exponent == E
        oracle = sp.solveset(sp.Abs(P) - 1, X, domain=sp.S.Reals).union(
            sp.solveset(E, X, domain=sp.S.Reals)
        ) - sp.FiniteSet(*sp.solve(P, X))
        assert a.stage.solution.intersect(sp.Interval.open(0, sp.oo)) == sp.FiniteSet(1)
        for p in [R(i, 2) for i in range(-8, 13)] + list(expected):
            base = abs(P.subs(X, p))
            exp = E.subs(X, p)
            if base == 0:
                assert not a.solution.contains(p)
                continue
            total = sp.N(base**exp + base ** (-exp), 50)
            assert bool(a.solution.contains(p)) == (
                abs(total - 2) < sp.Float("1e-35", 50)
            )
    else:
        a = signed_exponent(formula)
        assert a.base == P and sp.cancel(a.exponent.subs(a.symbol, sp.Abs(X)) - E) == 0
        oracle = sp.Union(
            *(
                sp.solve_univariate_inequality(
                    sp.Lt(E.subs(sp.Abs(X), sign * X), 0)
                    if a.operator == "<"
                    else sp.Le(E.subs(sp.Abs(X), sign * X), 0),
                    X,
                    relational=False,
                ).intersect(domain)
                for sign, domain in [
                    (1, sp.Interval(0, sp.oo)),
                    (-1, sp.Interval(-sp.oo, 0)),
                ]
            )
        )
        for p in [R(i, 2) for i in range(-14, 15)]:
            exponent = E.subs(X, p)
            if exponent.has(sp.zoo):
                assert not a.solution.contains(p)
                continue
            direct = sp.N(sp.Integer(P) ** exponent, 50)
            assert bool(a.solution.contains(p)) == bool(
                direct < 1 if a.operator == "<" else direct <= 1
            )
    same_set(a.solution, oracle)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_readonly_unchanged_input_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler(row).diagram_specs(ctx)
    )
    if row["method"] == "reciprocal":
        assert (
            p.solution_html.index("ненулевом основании")
            < p.solution_html.index("Сделаем замену")
            < p.solution_html.index("обратна первой")
            < p.solution_html.index("только при t=1")
            < p.solution_html.index("линейные уравнения")
        )
    else:
        assert (
            p.solution_html.index("нулевую степень")
            < p.solution_html.index("первый случай")
            < p.solution_html.index("второй случай")
            < p.solution_html.index("Объединяя")
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
        parent_solution_html=PARENTS[row["method"]],
    )
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


def test_zero_exponent_does_not_rescue_zero_modulus_base():
    a = reciprocal(r"|x-1|^{x-1}+|x-1|^{1-x}\le2")
    assert a.solution == sp.FiniteSet(0, 2) and 1 in a.poles


def test_all_cancelled_source_holes_in_base_and_exponents_are_retained():
    a = reciprocal(r"|\frac{(x-1)(x-2)}{x-2}|^{x+\frac{x}{x}-1}+|x-1|^{-x}\le2")
    assert a.solution == sp.EmptySet and set(a.poles) == {0, 1, 2}


def test_signed_cases_keep_a_cancelled_pole_in_the_numerator():
    a = signed_exponent(r"5^{\frac{x^2-7|x|+6+\frac{x-2}{x-2}-1}{(x-4)^2}}\le1")
    assert not a.solution.contains(2) and all(
        2 in stage.poles for _, stage, _ in a.cases
    )
    assert a.solution.contains(-2)


def test_decreasing_base_reverses_the_comparison_and_strictness_is_preserved():
    formula = r"\frac{1}{2}^{\frac{x^2-7|x|+6}{(x-4)^2}}\ge1"
    a = signed_exponent(formula)
    b = signed_exponent(formula.replace(r"\ge", r"\gt"))
    assert a.exponent_operator == "<=" and b.exponent_operator == "<"
    assert a.solution.contains(1) and not b.solution.contains(1)
    assert not a.solution.contains(4) and not b.solution.contains(4)


def test_zero_belongs_to_both_closed_sign_cases_when_valid():
    a = signed_exponent(r"2^{\frac{x^2+|x|-1}{(x-2)^2}}\le1")
    assert all(
        solution.contains(0) for _, _, solution in a.cases
    ) and a.solution.contains(0)


def test_reviewed_stray_dot_is_only_accepted_between_modulus_and_braced_power():
    formula = read_formula(ROWS[0]["context"])[1]
    assert "|.^{" in formula.replace(r"\right", "")
    same_set(
        reciprocal(formula).solution, reciprocal(formula.replace(".^{", "^{")).solution
    )
    with pytest.raises(UnsupportedCondition):
        reciprocal(formula.replace(".^{", "..^{"))


@pytest.mark.parametrize(
    "formula",
    [
        r"|x-1|^{x}+|x-1|^{1-x}\le2",
        r"|x-1|^{x}+|x-2|^{-x}\le2",
        r"|x-1|^{x}+|x-1|^{-x}<2",
        r"|x-1|^{x}+|x-1|^{-x}\le3",
        r"|x-1|^{x^2}+|x-1|^{-x^2}\le2",
        r"|x^2-1|^{x}+|x^2-1|^{-x}\le2",
        r"|x-1|^{x}+|x-1|^{-x}+1\le2",
        r"|x-1|^{x}\cdot|x-1|^{-x}\le2",
        r"|x-1|^{x}+|x-1|^{-x}.\le2",
        r"|x-1|^{x}+|x-1|^{-x}\le2+x",
        r"|x-1|^{|x|}+|x-1|^{-|x|}\le2",
    ],
)
def test_reciprocal_whole_ast_and_domain_shape_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        reciprocal(formula)


@pytest.mark.parametrize(
    "formula",
    [
        r"1^{\frac{x^2-7|x|+6}{(x-4)^2}}\le1",
        r"0^{\frac{x^2-7|x|+6}{(x-4)^2}}\le1",
        r"5^{\frac{x^2-7|x-1|+6}{(x-4)^2}}\le1",
        r"5^{\frac{x^2-7|x|+6}{(x-4)^2}}+1\le1",
        r"5^{\frac{x^2-7|x|+6}{(x-4)^2}}\le2",
        r"5^{\frac{x^2-7|x|+6}{(x-4)^2}}\le|x|",
        r"5^{\frac{x^3-7|x|+6}{(x-4)^2}}\le1",
        r"5^{\frac{x^2-7|x|+6}{x-4}}\le1",
        r"5^{\frac{x^2-7|x|+6}{(x-4)^2}}\le1\text{ extra}",
    ],
)
def test_signed_exponent_whole_ast_and_bounds_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        signed_exponent(formula)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_assets_and_full_instruction_guards(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]][-1])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_key": "unknown", "asset_id": "unreviewed"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительное условие</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
