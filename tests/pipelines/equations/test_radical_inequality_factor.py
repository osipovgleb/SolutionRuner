"""Independent original domains, zero branches and coefficient signs for six sources."""

import json
from pathlib import Path

import pytest
import sympy as sp
from test_exponential_inequality_preimages import answer_set

from solution_runner.pipelines.equations.radical_inequality_domains import domain
from solution_runner.pipelines.equations.radical_inequality_factor import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.equations.rational_substitution_preimages import (
    comparison,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("radical_inequality_sources.json")
        .read_text()
    )
    if r["group"] in ("507582", "485951")
]
QUOTIENTS = {"507582": (3, 5, 3, 4), "507593": (4, 6, 4, 5), "511445": (2, 4, 2, 3)}
ROOTS = {
    "485951": (
        6 * X - X**2,
        1 / (X**2 - 7 * X + 12) + (X - 4) / (3 - X),
        (3, 4),
        "<=",
        sp.Interval(0, 6),
    ),
    "508446": (
        -7 * X - X**2,
        (X + 5) / (X + 4) - 1 / (X**2 + 9 * X + 20),
        (-5, -4),
        ">=",
        sp.Interval(-7, 0),
    ),
    "511535": (
        -6 * X - X**2,
        (X + 4) / (X + 3) - 1 / (X**2 + 7 * X + 12),
        (-4, -3),
        ">=",
        sp.Interval(-6, 0),
    ),
}
ANSWERS = {
    "507582": r"(0;1]\cup\{2\}\cup[3;4)\cup(4;5]",
    "507593": r"(0;1]\cup\{3\}\cup[4;5)\cup(5;6]",
    "511445": r"(0;1]\cup[2;3)\cup(3;4]",
    "485951": r"[0;3)\cup(3;4)\cup[5;6]",
    "508446": r"[-7;-6]\cup(-5;-4)\cup(-4;0]",
    "511535": r"[-6;-5]\cup(-4;-3)\cup(-3;0]",
}


def original(task):
    if task in QUOTIENTS:
        c, k, b, m = QUOTIENTS[task]
        R = X + b / X - m
        P = (X - c) ** 2
        Q = k - X
        factor = ((sp.sqrt(P) - 1) / (sp.sqrt(Q) - 1)) ** 2
        D = sp.Interval(-sp.oo, k) - sp.FiniteSet(0, k - 1)
        zeros = sp.FiniteSet(c - 1, c + 1)
        return P, R, factor, D, zeros, ">="
    P, R, poles, op, root_domain = ROOTS[task]
    D = root_domain - sp.FiniteSet(*poles)
    return P, R, sp.sqrt(P), D, sp.FiniteSet(root_domain.start, root_domain.end), op


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_domain_zero_first_branches_and_manual_answer(row):
    a = analyze(read_formula(row["context"])[1])
    P, R, _factor, D, zeros, op = original(row["task"])
    assert sp.expand(a.numerator - P) == 0 and sp.cancel(a.stage.original - R) == 0
    assert a.constraints.values == D
    assert a.zero_candidates == zeros and a.zero_case == zeros.intersect(D)
    assert a.positive_domain == D - zeros
    oracle = sp.solve_univariate_inequality(
        R >= 0 if op == ">=" else R <= 0, X, relational=False
    )
    assert a.positive_case == oracle.intersect(D - zeros)
    assert a.solution == sp.Union(zeros.intersect(D), oracle.intersect(D - zeros))
    assert a.solution == answer_set(ANSWERS[row["task"]])
    assert a.operator == op


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_root_values_and_poles_independently_match_solution(row):
    a = analyze(read_formula(row["context"])[1])
    _P, R, factor, D, zeros, op = original(row["task"])
    samples = (
        {sp.Rational(n, 4) for n in range(-40, 41)}
        | set(zeros)
        | set(a.constraints.excluded)
    )
    for point in samples:
        if D.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        value = sp.simplify((R * factor).subs(X, point))
        expected = bool(value >= 0 if op == ">=" else value <= 0)
        assert bool(a.solution.contains(point)) == expected, (row["task"], point, value)


def test_squared_factor_zero_at_forbidden_root_denominator_is_never_added():
    a = analyze(read_formula(ROWS[0]["context"])[1])
    assert a.zero_candidates == sp.FiniteSet(2, 4)
    assert a.zero_case == sp.FiniteSet(2)
    assert a.constraints.excluded == (0, 4)
    assert a.stage.poles == (0,) and a.stage.holes == ()
    assert 4 not in a.stage.points
    assert a.stage.solution.contains(4) and not a.solution.contains(4)


@pytest.mark.parametrize(
    "task,hole,expected_signs",
    [
        ("485951", 3, (1, 1, -1, 1)),
        ("508446", -4, (1, -1, 1, 1)),
        ("511535", -3, (1, -1, 1, 1)),
    ],
)
def test_cancelled_rational_holes_remain_on_the_projected_sign_chart(
    task, hole, expected_signs
):
    row = next(r for r in ROWS if r["task"] == task)
    a = analyze(read_formula(row["context"])[1])
    assert a.stage.holes == (hole,) and hole in a.stage.points
    assert a.stage.signs == expected_signs
    assert a.stage.sign_operator == ">="
    assert not a.stage.solution.contains(hole) and not a.solution.contains(hole)


def test_new_comparison_option_preserves_original_pole_after_cancelled_factor():
    stage = comparison((X - 5) / (X - 4), ">=", denominators=(X - 3,))
    assert stage.points == (3, 4, 5) and stage.holes == (3,)
    assert stage.signs == (1, 1, -1, 1)
    assert stage.solution == sp.Union(
        sp.Interval.open(-sp.oo, 3), sp.Interval.open(3, 4), sp.Interval(5, sp.oo)
    )


def test_zero_root_does_not_rescue_an_original_undefined_coefficient():
    a = analyze(r"\frac{x}{x}\sqrt{6*x-x^2}\ge0")
    assert a.zero_candidates == sp.FiniteSet(0, 6)
    assert a.zero_case == sp.FiniteSet(6)
    assert a.solution == sp.Interval.Lopen(0, 6)
    assert a.stage.holes == (0,)


def test_root_domain_keeps_a_cancelled_pole_inside_the_radicand():
    a = analyze(r"\frac{1}{x-3}\sqrt{\frac{x-1}{x-1}+5*x-x^2}\ge0")
    assert 1 in a.constraints.excluded
    assert a.constraints.values.contains(1) is sp.false


def test_negative_root_level_does_not_create_a_false_exclusion():
    root = sp.Dummy("root", real=True)
    result = domain({root: X}, (root + 1,))
    assert result.excluded == () and result.values == sp.Interval(0, sp.oo)


@pytest.mark.parametrize(
    "denominator",
    [lambda r, s: r * s - 1, lambda r, s: r**2 - 1, lambda r, s: X * r - 1],
)
def test_unreviewed_radical_denominator_forms_are_rejected(denominator):
    r, s = sp.symbols("r s", real=True)
    with pytest.raises(UnsupportedCondition):
        domain({r: X, s: X + 1}, (denominator(r, s),))


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{6*x-x^2}<0",
        r"(x+\sqrt{6*x-x^2})\ge0",
        r"\frac{1}{x}\sqrt{x^2+1}\ge0",
        r"\frac{1}{x}\sqrt{6*x-x^2}\ge1",
        r"\frac{1}{x}\sqrt{6*x-x^2}+\sqrt{x+1}\ge0",
        r"(x+3/x)((\sqrt{x^2-6*x+10}-1)/(\sqrt{5-x}-1))^2\ge4*((\sqrt{x^2-6*x+10}-1)/(\sqrt{5-x}-1))^2",
        r"(x+3/x)((\sqrt{x^2-6*x+9}-2)/(\sqrt{5-x}-1))^2\ge4*((\sqrt{x^2-6*x+9}-2)/(\sqrt{5-x}-1))^2",
        r"(x+3/x)((\sqrt{x^2-6*x+9}-1)/(\sqrt{5-x}-1))^2\ge4*((\sqrt{x^2-6*x+9}-1)/(\sqrt{5-x}-1))^2+1",
    ],
)
def test_the_complete_original_expression_and_reviewed_factor_shape_are_required(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
