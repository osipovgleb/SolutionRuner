"""Common power identities on negative x, complete coefficients and uncancelled domains."""

import json
import math
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
from solution_runner.pipelines.equations.absolute_log_power import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("absolute_log_power_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "519640": (2, 5, 0, (1, 1), 2, X + 6, sp.Interval(-2, 3) - sp.FiniteSet(0)),
    "519673": (3, 2, 0, (1, 2), 3, 2 * X + 3, sp.Interval(-1, 3) - sp.FiniteSet(0)),
    "519684": (2, 3, 1, (1, 2), 4, 3 * X + 4, sp.Interval(-1, 4) - sp.FiniteSet(0)),
}


def handler():
    return get_handler(get_group_profile("519640").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_three_manual_answers_original_numeric_powers_on_both_sides_of_zero(row):
    a = analyze(read_formula(row["context"])[1])
    A, b, h, (c1, c2), total, Q, expected = MANUAL[row["task"]]
    assert (a.base, a.reference, a.shift, a.coefficients, a.total, a.argument) == (
        A,
        b,
        h,
        (c1, c2),
        total,
        Q,
    )
    oracle = sp.solve_univariate_inequality(
        X**2 <= Q, X, relational=False
    ) - sp.FiniteSet(0)
    same_set(a.solution, oracle)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    same_set(
        a.domain,
        sp.solve_univariate_inequality(Q > 0, X, relational=False) - sp.FiniteSet(0),
    )
    assert not a.solution.contains(0) and 0 in a.poles
    saw_negative = False
    saw_positive = False
    for point in [sp.Rational(i, 4) for i in range(-32, 33)]:
        q = Q.subs(X, point)
        if point == 0 or q <= 0:
            assert not a.domain.contains(point)
            continue
        x = float(point)
        first = A ** (h + math.log(x * x, b))
        second = abs(x) ** math.log(A * A, b)
        right = total * (1 / A) ** math.log(float(q), 1 / b)
        assert math.isclose(
            second, A ** math.log(x * x, b), rel_tol=1e-12, abs_tol=1e-12
        )
        lhs = c1 * first + c2 * second
        assert bool(a.solution.contains(point)) == (lhs <= right + 1e-10)
        saw_negative |= x < 0
        saw_positive |= x > 0
    assert saw_negative and saw_positive


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_left_right_reduction_order_readonly_unchanged_input_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler().diagram_specs(ctx)
    )
    assert (
        p.solution_html.index("область определения")
        < p.solution_html.index("Преобразуем левую")
        < p.solution_html.index("Преобразуем правую")
        < p.solution_html.index("Делим обе части")
        < p.solution_html.index("разложим квадратный")
        < p.solution_html.index("исключая нуль")
    )
    assert "(x^2)^{" in p.solution_html and "x^{2\\log" not in p.solution_html
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


@pytest.mark.parametrize(
    "before,after",
    [
        ("x^2", r"\frac{x^2(x-2)}{x-2}"),
        (r"\log_5 4", r"\log_5 (\frac{4(x-2)}{x-2})"),
        ("|x|", r"|\frac{x(x-2)}{x-2}|"),
        ("(x+6)", r"(\frac{(x+6)(x-2)}{x-2})"),
        (r"\frac{1}{2}", r"\frac{x-2}{2(x-2)}"),
    ],
)
def test_original_cancelled_holes_in_all_base_and_log_argument_parts_are_retained(
    before, after
):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    a = analyze(formula.replace(before, after, 1))
    assert 2 in a.poles and not a.domain.contains(2)
    same_set(a.solution, MANUAL["519640"][-1] - sp.FiniteSet(2))


@pytest.mark.parametrize(
    "before,after",
    [
        ("2^{", "3^{"),
        ("x^2", "x"),
        ("|x|", "|x-1|"),
        (r"\log_5 4", r"\log_5 8"),
        (r"\log_5 4", r"\log_3 4"),
        (r"\log_5 4", r"1+\log_5 4"),
        (r"\le 2\cdot", r"\le 3\cdot"),
        (r"\frac{1}{2}", r"\frac{1}{3}"),
        ("0.2", "0.5"),
        ("(x+6)", "(x^2+6)"),
        (r"\log_{0.2}", r"1+\log_{0.2}"),
        (r"\le", r"\lt"),
        (r"\le", r"\ge"),
    ],
)
def test_whole_power_bases_log_arguments_coefficient_identity_and_operator_required(
    before, after
):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(before, after, 1))


def test_constant_shift_is_accounted_for_in_the_complete_positive_coefficient_sum():
    formula = read_formula(ROWS[2]["context"])[1]
    assert analyze(formula).total == 4
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace("2^{1+", "2^{2+", 1))


@pytest.mark.parametrize("suffix", ["+1", r"\cdot2", r"\text{ extra}"])
def test_no_trailing_terms_or_instructions_are_discarded(suffix):
    with pytest.raises(UnsupportedCondition):
        analyze(read_formula(ROWS[0]["context"])[1] + suffix)


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
