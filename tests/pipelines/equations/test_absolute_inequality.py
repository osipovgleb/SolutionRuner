"""Source poles, isolated roots and exact inversion of a positive affine modulus."""

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
from solution_runner.pipelines.equations.absolute_inequality import (
    absolute_comparison,
    analyze,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("absolute_inequality_sources.json")
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
R = sp.sqrt(2)
MANUAL = {
    "507667": (
        X**2 - 10 * X,
        25,
        (-6, -1),
        sp.Union(
            sp.Interval(-sp.oo, -6, right_open=True),
            sp.Interval.Lopen(-6, 5 - 5 * R),
            sp.FiniteSet(5),
            sp.Interval(5 + 5 * R, sp.oo),
        ),
    ),
    "507670": (
        X**2 + 6 * X,
        9,
        (1, 4),
        sp.Union(
            sp.Interval(-sp.oo, -3 - 3 * R),
            sp.FiniteSet(-3),
            sp.Interval.Ropen(-3 + 3 * R, 4),
            sp.Interval.open(4, sp.oo),
        ),
    ),
    "511465": (
        X**2 - 8 * X,
        16,
        (-5, -1),
        sp.Union(
            sp.Interval.open(-sp.oo, -5),
            sp.Interval.Lopen(-5, 4 - 4 * R),
            sp.FiniteSet(4),
            sp.Interval(4 + 4 * R, sp.oo),
        ),
    ),
    "508405": (
        3 - 5 * X,
        3,
        (),
        sp.Union(
            sp.Interval.open(0, sp.Rational(3, 5)),
            sp.Interval.open(sp.Rational(3, 5), sp.Rational(6, 5)),
        ),
    ),
    "508407": (
        8 - 5 * X,
        4,
        (),
        sp.Union(
            sp.Interval.open(sp.Rational(4, 5), sp.Rational(8, 5)),
            sp.Interval.open(sp.Rational(8, 5), sp.Rational(12, 5)),
        ),
    ),
    "511515": (
        1 - 4 * X,
        4,
        (),
        sp.Union(
            sp.Interval.open(-sp.Rational(3, 4), sp.Rational(1, 4)),
            sp.Interval.open(sp.Rational(1, 4), sp.Rational(5, 4)),
        ),
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
def test_six_originals_manual_answers_and_independent_oracles(row):
    a = analyze(read_formula(row["context"])[1], row["method"])
    P, K, poles, expected = MANUAL[row["task"]]
    assert (a.argument, a.bound, a.poles) == (P, K, poles)

    def solve(expr):
        return sp.solve_univariate_inequality(expr, X, relational=False)

    if row["method"] == "squared_quotient":
        oracle = solve(P >= K).union(solve(P <= -K))
    else:
        oracle = solve(P < K).intersect(solve(P > -K)) - sp.FiniteSet(*sp.solve(P, X))
    same_set(a.solution, oracle - sp.FiniteSet(*poles))
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert all(not a.solution.contains(p) for p in poles)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_rational_or_polynomial_values_at_many_rational_points(row):
    a = analyze(read_formula(row["context"])[1], row["method"])
    P, K, poles, _expected = MANUAL[row["task"]]
    for point in {sp.Rational(n, 4) for n in range(-40, 41)} | set(
        map(sp.Integer, poles)
    ):
        if point in poles:
            assert not a.solution.contains(point)
            continue
        value = P.subs(X, point)
        if row["method"] == "squared_quotient":
            F, G = a.inverse_factors
            original = (1 / F.subs(X, point) - 1 / G.subs(X, point)) ** 2 <= abs(
                value
            ) / a.denominator.subs(X, point) ** 2
        else:
            original = value**2 - K * abs(value) < 0
        assert bool(a.solution.contains(point)) == bool(original)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_method_readonly_unchanged_input_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler(row).diagram_specs(ctx)
    )
    if row["method"] == "squared_quotient":
        assert (
            p.solution_html.index("общему знаменателю")
            < p.solution_html.index("ограничения")
            < p.solution_html.index("совокупность")
            < p.solution_html.index("Исключая")
        )
    else:
        assert (
            p.solution_html.index("выделим квадрат")
            < p.solution_html.index("Сделаем замену")
            < p.solution_html.index("квадратное неравенство")
            < p.solution_html.index("Вернёмся")
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


@pytest.mark.parametrize("operator", [">=", ">", "<=", "<"])
def test_generic_absolute_comparison_handles_negative_right_sides(operator):
    _, solution = absolute_comparison(X**2, operator, -1)
    assert solution == (sp.S.Reals if operator in (">=", ">") else sp.EmptySet)


def test_isolated_absolute_root_is_removed_if_it_is_an_original_pole():
    formula = read_formula(ROWS[0]["context"])[1].replace("x^{2}-10x", "x^{2}+2x-24")
    a = analyze(formula, "squared_quotient")
    assert (
        a.branches[1].solution == sp.FiniteSet(-1)
        and -1 in a.poles
        and not a.solution.contains(-1)
    )


def test_original_hole_inside_cancelled_absolute_argument_is_retained():
    formula = read_formula(ROWS[0]["context"])[1].replace(
        "x^{2}-10x", r"x^2-10x+\frac{x+10}{x+10}-1"
    )
    a = analyze(formula, "squared_quotient")
    assert -10 in a.poles and not a.solution.contains(-10)


def test_original_hole_is_kept_after_affine_absolute_substitution():
    formula = read_formula(ROWS[3]["context"])[1].replace(
        "3-5x", r"\frac{(3-5x)(x-\frac{1}{4})}{x-\frac{1}{4}}"
    )
    a = analyze(formula, "affine_substitution")
    assert (
        a.argument == 3 - 5 * X
        and a.poles == (sp.Rational(1, 4),)
        and not a.solution.contains(sp.Rational(1, 4))
    )


@pytest.mark.parametrize(
    "formula,method",
    [
        (
            r"((x+1)^{-1}-(x+6)^{-1})^2\ge\frac{|x^2-10x|}{(x^2+7x+6)^2}",
            "squared_quotient",
        ),
        (
            r"((x+1)^{-1}-(x+6)^{-1})^2\le\frac{|x^2-10x|}{(x^2+8x+6)^2}",
            "squared_quotient",
        ),
        (
            r"((x+1)^{-1}-(x+6)^{-1})^2\le\frac{|x^2-10x|+1}{(x^2+7x+6)^2}",
            "squared_quotient",
        ),
        (
            r"((x+1)^{-1}-(x+6)^{-1})^2\le\frac{|x^2-10x|+|x+1|}{(x^2+7x+6)^2}",
            "squared_quotient",
        ),
        (
            r"((x+1)^{-1}-(x+6)^{-1})^3\le\frac{|x^2-10x|}{(x^2+7x+6)^2}",
            "squared_quotient",
        ),
        (r"25x^2-3|3-5x|<30x-8", "affine_substitution"),
        (r"25x^2+3|3-5x|<30x-9", "affine_substitution"),
        (r"25x^2-3|3-5x|\le30x-9", "affine_substitution"),
        (r"25x^2-3|3-5x|+|x|<30x-9", "affine_substitution"),
        (r"25x^2-3|x^3|<30x-9", "affine_substitution"),
    ],
)
def test_whole_expression_parent_shape_and_polynomial_identity_guards(formula, method):
    with pytest.raises(UnsupportedCondition):
        analyze(formula, method)


@pytest.mark.parametrize("row", [ROWS[0], ROWS[3]], ids=lambda r: r["task"])
def test_parent_asset_instruction_and_saved_answer_guards(row):
    other = (
        "affine_substitution"
        if row["method"] == "squared_quotient"
        else "squared_quotient"
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, parent=PARENTS[other])
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(row, ctx).answer == plan(row).answer
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;0</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
