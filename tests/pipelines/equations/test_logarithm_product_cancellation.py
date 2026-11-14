"""Verify all source cases, uncancelled argument domains and the shared product method."""

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
from solution_runner.pipelines.equations.logarithm_inequality_planner import (
    build_context_repair_plan,
)
from solution_runner.pipelines.equations.logarithm_product_cancellation_proof import (
    render,
)
from solution_runner.pipelines.equations.logarithm_product_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_product_cancellation_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for row in ROWS
    if row["group"] == row["task"]
    for s in row["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
EXPECTED = {
    "561731": sp.Union(
        sp.Interval.Lopen(1, sp.Rational(7, 4)), sp.Interval.Ropen(4, 5)
    ),
    "561772": sp.Union(
        sp.Interval.Lopen(2, sp.Rational(18, 5)), sp.Interval.Ropen(5, 6)
    ),
    "639952": sp.Interval.Lopen(3, 4),
    "640521": sp.Interval.Lopen(2, 3),
}


def handler():
    return get_handler(get_group_profile("561731").content_rule_key)


def model(row):
    return analyze(read_formula(row["context"])[1], method="product_cancellation")


def plan(ctx, parent=PARENT):
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_source_answers_and_independent_cas_domains(row):
    a = model(row)
    same_set(a.solution, EXPECTED[row["task"]])
    same_set(answer_set(row["expected_answer"]), a.solution)
    domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg > 0, X, relational=False)
            for arg in a.arguments
        )
    )
    same_set(a.domain, domain)
    assert a.displayed_indices == (0, 1, 2) and a.full_stage is None
    A, B, C = a.arguments
    assert (
        sp.cancel(a.stage.original - (A * B - a.base ** (-a.constant_offset) * C)) == 0
    )
    _, denominator = sp.fraction(B)
    for pole in sp.solve(denominator, X):
        assert a.solution.contains(pole) is sp.false
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_actual_original_logarithms_on_rational_samples_and_boundaries(row):
    task = row["task"]
    base, offset, A, B, C = {
        "561731": (
            2,
            2,
            (X - 1) * (10 + 3 * X - X**2),
            (7 - X) / (10 + 3 * X - X**2),
            9 * X,
        ),
        "561772": (
            5,
            1,
            (X - 2) * (24 + 2 * X - X**2),
            (9 - X) / (24 + 2 * X - X**2),
            12 * X,
        ),
        "639952": (
            4,
            1,
            (X - 3) * (10 + 3 * X - X**2),
            (7 - X) / (10 + 3 * X - X**2),
            2 * X + 4,
        ),
        "640521": (
            2,
            1,
            (X - 2) * (4 + 3 * X - X**2),
            (6 - X) / (4 + 3 * X - X**2),
            X + 3,
        ),
    }[task]
    a = model(row)
    for point in (
        -3,
        -2,
        0,
        1,
        sp.Rational(3, 2),
        sp.Rational(7, 4),
        2,
        3,
        sp.Rational(18, 5),
        4,
        sp.Rational(9, 2),
        5,
        6,
        7,
        9,
    ):
        args = [sp.cancel(v.subs(X, point)) for v in (A, B, C)]
        if any(v.has(sp.zoo, sp.nan) or v.is_positive is not True for v in args):
            assert a.solution.contains(point) is sp.false
            continue
        numerator = (
            sp.log(args[0]) + sp.log(args[1]) - sp.log(args[2]) + offset * sp.log(base)
        )
        direct = sp.N(sp.simplify(sp.expand_log(numerator)), 50)
        assert bool(a.solution.contains(point)) == bool(direct <= 0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_preparation_original_conditions_no_figures_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(ctx)
    assert (
        ctx == before
        and not handler().diagram_specs(ctx)
        and "<img " not in p.solution_html
    )
    assert "сохраняя исходные ограничения" in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
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
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(ctx).transformations


@pytest.mark.parametrize("hole", [sp.Rational(3, 2), sp.Rational(17, 4)])
def test_cancelled_original_argument_poles_are_retained_after_product_cancellation(
    hole,
):
    raw = sp.latex(hole)
    formula = (
        r"\log_2((x-1)(10+3x-x^2))+\log_2(\frac{7-x}{10+3x-x^2})\le-2+\log_2(\frac{9x(x-"
        + raw
        + r")}{x-"
        + raw
        + "})"
    )
    a = analyze(formula, method="product_cancellation")
    same_set(a.solution, EXPECTED["561731"] - sp.FiniteSet(hole))
    assert a.argument_holes == (hole,)
    assert raw in render(a)
    assert model(ROWS[0]).stage.solution.contains(5) is sp.true
    assert model(ROWS[0]).solution.contains(5) is sp.false


def test_strict_endpoints_and_decreasing_logarithm_base():
    formula = read_formula(ROWS[0]["context"])[1]
    strict = analyze(formula.replace(r"\le", "<"), method="product_cancellation")
    same_set(
        strict.solution,
        sp.Union(sp.Interval.open(1, sp.Rational(7, 4)), sp.Interval.open(4, 5)),
    )
    decreasing = analyze(
        formula.replace(r"\log_2", r"\log_{(0{,}5)}"), method="product_cancellation"
    )
    assert decreasing.base == sp.Rational(1, 2) and decreasing.solution == sp.EmptySet
    assert "меньше" in render(decreasing) and "меняется" in render(decreasing)


@pytest.mark.parametrize(
    "replacement",
    [
        ("-2+", "-5+"),
        ("-2+", r"-\frac{1}{2}+"),
        ("-2+", "x-2+"),
        (r"\log_2 (9x)", r"\log_3 (9x)"),
        ("(x-1)(10+3x-x^{2})", "(x-1)"),
        (r"\frac{7-x}{10+3x-x^{2}}", r"\frac{7-x}{11+3x-x^{2}}"),
        ("(9x)", "(9x^2)"),
        (r"\log_2 ((x-1)", r"2\log_2 ((x-1)"),
    ],
)
def test_outside_complete_product_cancellation_grammar_fails_closed(replacement):
    formula = read_formula(ROWS[0]["context"])[1]
    old, new = replacement
    assert old in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(old, new, 1), method="product_cancellation")


def test_old_methods_do_not_silently_accept_product_offset_and_parent_is_pinned():
    formula = read_formula(ROWS[0]["context"])[1]
    for method in ("product", "quotient"):
        with pytest.raises(UnsupportedCondition):
            analyze(formula, method=method)
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0]["context"], PARENT + "changed")
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(
            ROWS[0]["context"], parent_solution_html=PARENT, method="product"
        )
    ctx = deepcopy(ROWS[0]["context"])
    expected = plan(ctx).answer
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == expected
    ctx["normalized_content"]["assets"] = [{"asset_id": "foreign"}]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
