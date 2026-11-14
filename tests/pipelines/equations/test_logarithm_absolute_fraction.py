"""Both positive-factor proofs, exact powered arguments and uncancelled source poles."""

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
from solution_runner.pipelines.equations.logarithm_absolute_fraction import analyze
from solution_runner.pipelines.equations.logarithm_absolute_fraction_input import read
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_absolute_fraction_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "507691": (
        X**2 + X,
        X**2 + 2 * X - 2,
        X - 1,
        10,
        1,
        2,
        sp.Union(sp.Interval(-sp.oo, -3), sp.Interval.open(1, sp.oo)),
    ),
    "507693": (
        X**2 + X,
        X**2 + 4 * X - 4,
        X - 2,
        8,
        1,
        6,
        sp.Union(
            sp.Interval(-sp.oo, -5), sp.Interval.Ropen(1, 2), sp.Interval.open(2, sp.oo)
        ),
    ),
    "511474": (
        X**2 + 3 * X,
        X**2 + 2 * X - 2,
        X - 1,
        10,
        2,
        2,
        sp.Union(sp.Interval(-sp.oo, -3), sp.Interval.open(1, sp.oo)),
    ),
}


def handler():
    return get_handler(get_group_profile("507691").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_three_manual_answers_domains_and_independent_original_values(row):
    a = analyze(read_formula(row["context"])[1])
    C, A, D, b, c, m, expected = MANUAL[row["task"]]
    assert (
        a.coefficient,
        a.argument,
        a.denominator,
        a.base,
        a.right_scalar,
        a.degree,
    ) == (C, A, D, b, c, m)
    oracle_domain = sp.solve_univariate_inequality(
        A > 0, X, relational=False
    ) - sp.FiniteSet(*sp.solve(D, X))
    same_set(a.domain, oracle_domain)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    for point in [sp.Rational(i, 2) for i in range(-16, 17)]:
        argument = A.subs(X, point)
        denominator = D.subs(X, point)
        if argument <= 0 or denominator == 0:
            assert not a.domain.contains(point) and not a.solution.contains(point)
            continue
        lhs = (
            float(C.subs(X, point))
            * math.log(float(argument), b)
            / abs(float(denominator))
        )
        rhs = c * math.log(float((-argument) ** m), b) / float(denominator)
        assert bool(a.solution.contains(point)) == (lhs >= rhs - 1e-11)
    for sign, solution in a.cases:
        sign_domain = sp.solve_univariate_inequality(
            D > 0 if sign == 1 else D < 0, X, relational=False
        )
        same_set(solution, expected.intersect(sign_domain))
        coefficient = sp.cancel((C - sign * c * m) / (sign * D))
        assert sign_domain.is_subset(
            sp.solve_univariate_inequality(coefficient > 0, X, relational=False)
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_case_order_positive_proofs_readonly_unchanged_input_and_replay(row):
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
        < p.solution_html.index("свойству логарифма")
        < p.solution_html.index("случай положительного")
        < p.solution_html.index("линейный коэффициент")
        < p.solution_html.index("случай отрицательного")
        < p.solution_html.index("Числитель коэффициента")
        < p.solution_html.index("Объединяя")
    )
    assert p.solution_html.count("Делим на строго положительный коэффициент") == 2
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


def test_even_sixth_argument_is_certified_in_factored_form_without_weakening_old_bounds():
    formula = read_formula(ROWS[1]["context"])[1]
    _, second, _, _, _ = read(formula)
    power = second[1]
    assert (
        isinstance(power, sp.Pow)
        and power.exp == 6
        and power.base == -MANUAL["507693"][1]
    )
    assert sp.degree(power, X) == 12
    with pytest.raises(UnsupportedCondition):
        RationalParser(r"(-x^2-4x+4)^6").parse()


@pytest.mark.parametrize(
    "where", ["left_argument", "right_argument", "coefficient", "modulus"]
)
def test_original_cancelled_holes_are_retained_in_all_four_input_parts(where):
    formula = read_formula(ROWS[0]["context"])[1]
    if where == "left_argument":
        formula = formula.replace("x^{2}+2x-2", r"x^2+2x-2+\frac{x-4}{x-4}-1", 1)
        point = 4
    elif where == "right_argument":
        formula = formula.replace("-x^{2}-2x+2", r"-x^2-2x+2+\frac{x+4}{x+4}-1", 1)
        point = -4
    elif where == "coefficient":
        formula = formula.replace("x^{2}+x", r"x^2+x+\frac{x-3}{x-3}-1", 1)
        point = 3
    else:
        formula = formula.replace(
            r"\left|x-1\right|", r"\left|x-1+\frac{x-4}{x-4}-1\right|", 1
        )
        point = 4
    a = analyze(formula)
    assert (
        point in a.poles
        and not a.domain.contains(point)
        and not a.solution.contains(point)
    )
    same_set(a.solution, MANUAL["507691"][-1] - sp.FiniteSet(point))


def test_positive_linear_coefficient_may_vanish_only_at_the_excluded_split_point():
    formula = read_formula(ROWS[0]["context"])[1].replace("x^{2}+x", "x^2-2x+3", 1)
    a = analyze(formula)
    assert a.positive_coefficient == X - 1 and not a.solution.contains(1)
    same_set(a.solution, MANUAL["507691"][-1])


@pytest.mark.parametrize(
    "before,after",
    [
        ("(x^{2}+x)", "x^2+x"),
        ("(x^{2}+x)", "(x^2+10x-9)"),
        ("(x^{2}+x)", "(x^2-5x+6)"),
        ("(x^{2}+x)", "(x^2+x-1)"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"\lg (-x^2-2x+3)^2"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"\lg (-x^2-2x+2)^3"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"\lg (-x^2-2x+2)^10"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"\lg^2(-x^2-2x+2)"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"\log_2(-x^2-2x+2)^2"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"*\lg (-x^2-2x+2)^2"),
        (r"\lg (-x^{2}-2x+2)^{2}", r"-2\lg (-x^2-2x+2)^2"),
        (r"\left|x-1\right|", r"\left|x-2\right|"),
        (r"\ge", r"\le"),
        (r"\ge", r"\gt"),
    ],
)
def test_full_coefficient_positivity_power_base_denominator_and_operator_guards(
    before, after
):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(before, after, 1))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_assets_and_instruction_guards(row):
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
