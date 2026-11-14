"""Original logarithm domains, rationalized signs and read-only parent proofs."""

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
from solution_runner.pipelines.equations.logarithm_rationalization import (
    ratio,
    square_denominator,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_rationalization_sources.json")
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
    "507764": (5 * X**2 - 2 * X + 1, 4 * X**2 - 5 * X + 1, 3, "<=", None),
    "507767": (3 * X**2 - 2 * X + 1, 5 * X**2 - 6 * X + 1, 5, ">=", None),
    "507770": (3 * X**2 + 2 * X - 1, 5 * X**2 + 3 * X - 2, 5, ">=", 0),
    "507784": (3 * X**2 + 2 * X - 1, 5 * X**2 + 3 * X - 2, 3, ">=", 1),
    "511485": (9 * X**2 - 3 * X + 1, 8 * X**2 - 6 * X + 1, 3, "<=", None),
    "511487": (3 * X**2 + 2 * X - 2, 5 * X**2 + 3 * X - 3, 3, ">=", 0),
    "642732": (3 - X, X + 2, 3, -1),
    "665353": (2 - X, X + 1, 2, -1),
    "674972": (3 - X, X + 1, 4, -2),
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
    return (ratio if row["method"] == "ratio_rationalization" else square_denominator)(
        read_formula(row["context"])[1]
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_answers_manual_arguments_and_independent_log_values(row):
    a = model(row)
    A, B, *data = MANUAL[row["task"]]
    assert a.A == A and a.B == B
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert plan(row).answer == a.answer
    for point in (sp.Rational(i, 20) for i in range(-61, 62)):
        if row["method"] == "ratio_rationalization":
            k, operator, shift = data
            assert (
                a.power == k and a.operator == operator and a.coordinate.shift == shift
            )
            original = point if shift is None else point**2 - shift
            if shift is not None and point < 0:
                continue
            av, bv = float(A.subs(X, point)), float(B.subs(X, point))
            valid = av > 0 and bv > 0 and bv != 1
            value = math.log(av) / (k * math.log(bv)) - 1 / k if valid else None
        else:
            base, level = data
            assert a.base == base and a.level == level
            original = point
            av, bv = float(A.subs(X, point)), float(B.subs(X, point))
            valid = (
                av > 0
                and bv > 0
                and point != 0
                and point**2 != sp.Integer(base) ** level
            )
            value = (
                (math.log(av, base) - math.log(bv, base))
                / (math.log(float(point**2), base) - level) ** 2
                if valid
                else None
            )
            operator = a.operator
        expected = valid and (value >= -1e-10 if operator == ">=" else value <= 1e-10)
        assert bool(a.solution.contains(original)) == expected, (row["task"], point)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_runtime_replays_without_writing_conditions_or_assets(row):
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
    assert gateway.reads == [ctx["problem_id"]] and record["status"] == "prepared"
    assert record["transformations"] == list(p.transformations)
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_holes_survive_rationalization(row):
    a = model(row)
    if row["method"] == "ratio_rationalization":
        for root in a.holes:
            if a.coordinate.shift is not None and root < 0:
                continue
            original = (
                root
                if a.coordinate.shift is None
                else sp.expand(root**2 - a.coordinate.shift)
            )
            assert a.solution.contains(original) is sp.false
        same_set(a.full_stage.solution.intersect(a.domain), a.working_solution)
    else:
        for root in (0, -sp.sqrt(a.threshold), sp.sqrt(a.threshold)):
            assert a.solution.contains(root) is sp.false


def test_shifted_root_retains_negative_original_x_and_argument_zero_stays_open():
    shifted = model(next(r for r in ROWS if r["task"] == "507784"))
    assert shifted.solution.contains(-sp.Rational(3, 4)) is sp.true
    lower = model(next(r for r in ROWS if r["task"] == "511487"))
    point = (8 - 2 * sp.sqrt(7)) / 9
    assert lower.solution.contains(point) is sp.false
    assert sp.simplify(lower.A.subs(X, (sp.sqrt(7) - 1) / 3)) == 0


@pytest.mark.parametrize("group", ["507764", "642732"])
def test_parent_answer_and_asset_guards(group):
    row = next(r for r in ROWS if r["group"] == group and r["task"] != group)
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    assert plan(row, ctx).answer == model(row).answer
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        (r"\le", r"\le 1+"),
        ("^{3}", "^{2}"),
        (r"\lg (5", r"\ln (5"),
        ("5y^{2}", "5q^{2}"),
        ("5y^{2}", r"\frac{y}{y}5y^{2}"),
        ("5y^{2}", "5y^{21}"),
    ],
)
def test_ratio_rejects_incomplete_mixed_reference_hidden_poles_and_unreviewed_powers(
    old, new
):
    formula = read_formula(ROWS[0]["context"])[1]
    assert old in formula
    with pytest.raises(UnsupportedCondition):
        ratio(formula.replace(old, new, 1))


@pytest.mark.parametrize("suffix", ["+1", "+x", "+0"])
def test_outer_fraction_must_be_consumed_completely(suffix):
    formula = read_formula(ROWS[0]["context"])[1]
    with pytest.raises(UnsupportedCondition):
        ratio(formula.replace(r"\le", suffix + r"\le", 1))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_rational_signs_and_domains_against_independent_cas(row):
    a = model(row)
    A, B, *data = MANUAL[row["task"]]
    relation = {">=": sp.Ge, "<=": sp.Le}[a.operator]
    oracle = sp.solve_univariate_inequality(A > 0, X, relational=False).intersect(
        sp.solve_univariate_inequality(B > 0, X, relational=False)
    )
    if row["method"] == "ratio_rationalization":
        oracle -= sp.solveset(B - 1, X, domain=sp.S.Reals)
        oracle = oracle.intersect(
            sp.solve_univariate_inequality(
                relation((A - B) * (B - 1), 0), X, relational=False
            )
        )
        if a.coordinate.shift is not None:
            oracle = oracle.intersect(sp.Interval(0, sp.oo))
        same_set(a.working_solution, oracle)
    else:
        base, level = data
        oracle -= sp.FiniteSet(
            0, -sp.sqrt(sp.Integer(base) ** level), sp.sqrt(sp.Integer(base) ** level)
        )
        same_set(
            a.solution,
            oracle.intersect(
                sp.solve_univariate_inequality(relation(A - B, 0), X, relational=False)
            ),
        )


@pytest.mark.parametrize(
    "old,new",
    [
        ("+1}", "+2}"),
        (r"\log_3 (x+2)", r"\log_2 (x+2)"),
        ("x^{4}", "x^{3}"),
        ("3-x", "3-x^{2}"),
        ("3-x", r"3-\frac{x-1}{x-1}x"),
        (r"\ge 0", r"\ge 1"),
    ],
)
def test_square_denominator_rejects_non_square_mixed_bases_and_original_hidden_poles(
    old, new
):
    row = next(r for r in ROWS if r["task"] == "642732")
    formula = read_formula(row["context"])[1]
    assert old in formula
    with pytest.raises(UnsupportedCondition):
        square_denominator(formula.replace(old, new, 1))
