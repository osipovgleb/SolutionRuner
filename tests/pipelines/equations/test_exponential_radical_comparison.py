"""Original exponential-root domains, unsquared branches and exact read-only plans."""

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
from solution_runner.pipelines.equations.exponential_radical_comparison import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("exponential_radical_sources.json")
        .read_text()
    )
    if r["group"] == "508540"
]
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "508540": (3, 2 * X**2 - 21 * X + 10, X - 10, sp.Rational(1, 2), sp.Integer(10)),
    "508542": (2, 3 * X**2 - 10 * X + 3, X - 3, sp.Rational(1, 3), sp.Integer(3)),
    "511567": (2, 2 * X**2 - 17 * X + 8, X - 8, sp.Rational(1, 2), sp.Integer(8)),
}


def handler():
    return get_handler(get_group_profile("508540").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_originals_against_independent_unsquared_domain_cases(row):
    a = analyze(read_formula(row["context"])[1])
    base, Q, R, lo, hi = MANUAL[row["task"]]
    assert (a.base, a.exponent, a.radicand, a.right) == (base, X, Q, R)
    positive = sp.Interval.open(0, sp.oo)

    def solve(expr):
        return sp.solve_univariate_inequality(expr, X, relational=False)

    oracle = (
        solve(Q >= 0)
        .intersect(solve(R < 0).union(solve(R >= 0).intersect(solve(Q - R**2 >= 0))))
        .intersect(positive)
    )
    expected = sp.Union(sp.Interval.Lopen(0, lo), sp.Interval(hi, sp.oo))
    same_set(a.positive_solution, oracle)
    same_set(a.positive_solution, expected)
    expected_x = sp.Union(
        sp.Interval(-sp.oo, sp.log(lo) / sp.log(base)),
        sp.Interval(sp.log(hi) / sp.log(base), sp.oo),
    )
    same_set(a.solution, expected_x)
    same_set(answer_set(plan(row).answer), expected_x)
    # The left root must survive although blind squaring would discard it.
    assert Q.subs(X, lo) == 0 and R.subs(X, lo) < 0 and (Q - R**2).subs(X, lo) < 0
    assert a.negative_case.contains(lo) and a.positive_solution.contains(lo)
    assert a.nonnegative_case.contains(hi) and a.positive_solution.contains(hi)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_actual_root_values_on_both_branches_and_forbidden_middle(row):
    a = analyze(read_formula(row["context"])[1])
    _, Q, R, lo, hi = MANUAL[row["task"]]
    for point in {
        lo / 2,
        lo,
        (lo + hi) / 2,
        hi,
        hi + 1,
        sp.Rational(1, 10),
        sp.Integer(1),
    }:
        q, r = Q.subs(X, point), R.subs(X, point)
        expected = q >= 0 and bool(sp.sqrt(q) >= r)
        assert bool(a.positive_solution.contains(point)) == expected
    assert not a.positive_solution.contains(0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_method_order_readonly_runtime_unchanged_input_and_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == original
        and not handler().diagram_specs(ctx)
        and "<img" not in p.solution_html
    )
    assert (
        p.solution_html.index("Пусть")
        < p.solution_html.index("Область определения")
        < p.solution_html.index("В первом случае")
        < p.solution_html.index("Во втором случае")
        < p.solution_html.index("возвести их в квадрат")
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
        handler().key,
        parent_solution_html=PARENT,
    )
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


def test_negative_exponent_reverses_the_inverse_order():
    a = analyze(r"\sqrt{2\cdot 9^{-x}-7\cdot 3^{-x+1}+10}\ge3^{-x}-10")
    same_set(
        a.solution,
        sp.Union(
            sp.Interval(-sp.oo, -sp.log(10) / sp.log(3)),
            sp.Interval(sp.log(2) / sp.log(3), sp.oo),
        ),
    )


def test_affine_exponent_shift_is_retained_in_inverse():
    a = analyze(r"\sqrt{2\cdot 9^{2x+1}-7\cdot 3^{2x+2}+10}\ge3^{2x+1}-10")
    same_set(
        a.solution,
        sp.Union(
            sp.Interval(-sp.oo, (-sp.log(2) / sp.log(3) - 1) / 2),
            sp.Interval((sp.log(10) / sp.log(3) - 1) / 2, sp.oo),
        ),
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\le3^x-10",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}+1\ge3^x-10",
        r"2\sqrt{2\cdot9^x-21\cdot3^x+10}\ge3^x-10",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\ge3^x-10\ge0",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\ge x-10",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\ge5^x-10",
        r"\sqrt{2\cdot9^{x^2}-21\cdot3^{x^2}+10}\ge3^{x^2}-10",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\ge10-3^x",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10}\ge3^x-9",
        r"\sqrt{2\cdot9^x-21\cdot3^x+10+\frac{x-1}{x-1}-1}\ge3^x-10",
        r"\sqrt{4-3^x}\ge3^x-4",
    ],
)
def test_whole_condition_and_parent_method_guards(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_saved_answer_is_not_an_input_to_the_calculation():
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ROWS[0], ctx).answer == plan(ROWS[0]).answer


def test_unknown_parent_is_rejected():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + " ")


def test_unreviewed_source_figure_is_rejected():
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_key": "image_1", "asset_id": "unreviewed"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


def test_extra_condition_instruction_is_rejected():
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;0</p>"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


def test_squaring_can_remove_part_of_the_upper_domain_branch():
    a = analyze(r"\sqrt{\frac{9^x-5\cdot3^x+4}{2}}\ge3^x-4")
    same_set(a.positive_solution, sp.Union(sp.Interval.Lopen(0, 1), sp.Interval(4, 7)))
    assert not a.positive_solution.contains(8)
    assert a.domain.contains(8)
