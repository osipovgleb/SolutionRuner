"""Original logarithm domains, exact exponential identities and read-only repairs."""

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
from solution_runner.pipelines.equations.logarithm_exponential import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_exponential_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "507503": (
        5,
        10,
        2 * X + 1,
        2 * X - 1,
        4,
        sp.Rational(1, 10),
        sp.Rational(1, 50),
        sp.Rational(1, 5),
    ),
    "507682": (
        3,
        6,
        X + 1,
        X - 1,
        2,
        sp.Rational(1, 6),
        sp.Rational(1, 18),
        sp.Rational(1, 3),
    ),
    "511438": (3, 6, 2 * X, 2 * X + 1, 4, sp.Integer(2), sp.Integer(3), sp.Integer(3)),
    "511471": (2, 6, X - 1, X + 1, 3, sp.Integer(1), sp.Integer(12), sp.Integer(4)),
}


def handler():
    return get_handler(get_group_profile("507503").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_every_original_against_manual_answer_and_independent_quadratic(row):
    a = analyze(read_formula(row["context"])[1])
    B, M, A, R, C, d, K, upper = MANUAL[row["task"]]
    assert (
        a.logarithm_base,
        a.constant_argument,
        a.coefficient,
        a.right,
        a.base,
        a.exponent,
        a.shift,
        a.bound,
    ) == (B, M, A, R, C, X, d, K)
    oracle = sp.solve_univariate_inequality(
        X**2 - d * X - K <= 0, X, relational=False
    ).intersect(sp.Interval.open(d, sp.oo))
    same_set(a.positive_solution, oracle)
    same_set(a.positive_solution, sp.Interval.Lopen(d, upper))
    expected = sp.Interval.Lopen(sp.log(d) / sp.log(C), sp.log(upper) / sp.log(C))
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert not a.positive_solution.contains(d) and a.positive_solution.contains(upper)
    assert a.stage.original.subs(X, upper) == 0 and a.stage.original.subs(X, d) == -K


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithms_and_positive_power_identity(row):
    a = analyze(read_formula(row["context"])[1])
    B, M, A, R, C, d, K, _upper = MANUAL[row["task"]]
    for x in map(sp.Rational, [-2, -1, 0, sp.Rational(1, 2), 1, 2]):
        y = sp.Integer(C) ** x
        ratio = sp.simplify(
            sp.Integer(M) ** A.subs(X, x) / sp.Integer(B) ** R.subs(X, x)
        )
        assert sp.simplify(ratio - y / K) == 0
        if y <= d:
            assert not a.solution.contains(x)
            continue
        difference = (
            sp.log(M) / sp.log(B) * A.subs(X, x)
            + sp.log(y - d) / sp.log(B)
            - R.subs(X, x)
        )
        numeric = difference.evalf(50)
        if abs(numeric) > sp.Rational(1, 10) ** 40:
            assert bool(a.solution.contains(x)) == bool(numeric < 0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_readonly_unchanged_input_and_idempotence(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and not handler().diagram_specs(ctx)
        and "<img" not in p.solution_html
    )
    assert (
        p.solution_html.index("систему")
        < p.solution_html.index("Решим второе")
        < p.solution_html.index("Пусть")
        < p.solution_html.index("квадратное")
        < p.solution_html.index("Учитывая первое")
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


def test_negative_exponent_reverses_open_and_closed_inverse_endpoints():
    a = analyze(r"(-2x+1)\log_5 10+\log_5(4^{-x}-\frac{1}{10})\le-2x-1")
    same_set(
        a.solution, sp.Interval.Ropen(sp.log(5) / sp.log(4), sp.log(10) / sp.log(4))
    )


def test_affine_coordinate_shift_survives_the_positive_exponential_quotient():
    a = analyze(r"(2x+3)\log_5 10+\log_5(4^{x+1}-\frac{1}{10})\le2x+1")
    assert a.exponent == X + 1 and a.bound == sp.Rational(1, 50)
    same_set(
        a.solution,
        sp.Interval.Lopen(
            sp.log(sp.Rational(1, 10)) / sp.log(4) - 1,
            sp.log(sp.Rational(1, 5)) / sp.log(4) - 1,
        ),
    )


def test_implicit_and_explicit_multiplication_have_the_same_math():
    formula = read_formula(ROWS[0]["context"])[1]
    assert (
        analyze(formula).solution
        == analyze(formula.replace("2x", r"2\cdot x")).solution
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10})\ge2x-1",
        r"(2x+1)\log_5 11+\log_5(4^x-\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_3(4^x-\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10})+1\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10})\le2x-1\le0",
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10})^2\le2x-1",
        r"(x^2+1)\log_5 10+\log_5(4^x-\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^{x^2}-\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x+x-\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x+\frac{1}{10})\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10}+\frac{x-1}{x-1}-1)\le2x-1",
        r"(2x+1)\log_5 10+\log_5(4^x-\frac{1}{10})\le\frac{(2x-1)(x-1)}{x-1}",
        r"(2x+1000000)\log_5 10+\log_5(4^x-\frac{1}{10})\le2x-1",
    ],
)
def test_whole_condition_identity_and_original_denominator_guards(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_nonincreasing_log_base_is_outside_the_parent_method():
    with pytest.raises(UnsupportedCondition):
        analyze(
            r"(2x+1)\log_{\frac{1}{5}}10+\log_{\frac{1}{5}}(4^x-\frac{1}{10})\le2x-1"
        )


def test_parent_asset_and_extra_instruction_guards_and_saved_answer_ignored():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + " ")
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ROWS[0], ctx).answer == plan(ROWS[0]).answer
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;0</p>"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
