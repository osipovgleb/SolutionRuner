"""Exact radical roots, endpoint order and original holes remain independently checked."""

import pytest
import sympy as sp

from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.equations.rational_inequality_roots import (
    ordered,
    real_roots,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition


@pytest.mark.parametrize(
    "formula,expected",
    [
        (
            r"\frac{x}{x^2-2}>0",
            sp.Interval.open(-sp.sqrt(2), 0) | sp.Interval.open(sp.sqrt(2), sp.oo),
        ),
        (r"x^2+(2-\sqrt{15})x-2\sqrt{15}\le0", sp.Interval(-2, sp.sqrt(15))),
        (r"x^2-(3+\sqrt{5})x+3\sqrt{5}\le0", sp.Interval(sp.sqrt(5), 3)),
        (
            r"\frac{x^2-2}{x-\sqrt{2}}\ge0",
            sp.Interval(-sp.sqrt(2), sp.oo) - sp.FiniteSet(sp.sqrt(2)),
        ),
        (
            r"\frac{1}{x-1}+\frac{1}{2-x}\le5",
            sp.Interval.open(-sp.oo, 1)
            | sp.Interval((15 - sp.sqrt(5)) / 10, (15 + sp.sqrt(5)) / 10)
            | sp.Interval.open(2, sp.oo),
        ),
        (
            r"\frac{20+x-x^2}{x^2-5x}\le1-\frac{2}{x-1}",
            sp.Interval(-sp.oo, -sp.sqrt(2))
            | sp.Interval.open(0, 1)
            | sp.Interval.Ropen(sp.sqrt(2), 5)
            | sp.Interval.open(5, sp.oo),
        ),
    ],
)
def test_exact_radical_intervals_against_independent_sympy_solver(formula, expected):
    a = analyze(formula)
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.poles)
    assert a.solution == expected == independent
    assert all(p not in a.solution for p in a.poles)


def test_exact_order_separates_close_irrational_boundaries_and_deduplicates_equal_forms():
    values = (
        sp.sqrt(2),
        sp.Rational(1414213562373, 10**12),
        1 / sp.sqrt(2),
        sp.sqrt(2) / 2,
    )
    assert ordered(values) == (
        sp.sqrt(2) / 2,
        sp.Rational(1414213562373, 10**12),
        sp.sqrt(2),
    )
    assert real_roots(X**2 + (2 - sp.sqrt(15)) * X - 2 * sp.sqrt(15)) == (
        -2,
        sp.sqrt(15),
    )
    assert real_roots(X**2 - (3 + sp.sqrt(5)) * X + 3 * sp.sqrt(5)) == (sp.sqrt(5), 3)


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{x}>0",
        r"\sqrt{-1}x>0",
        r"\sqrt{1000001}x>0",
        r"(\sqrt{2}+\sqrt{3}+\sqrt{5})x>0",
        r"\frac{1}{1000000000}^8x>0",
        r"x^3-x-1>0",
    ],
)
def test_unreviewed_or_unbounded_algebraic_input_still_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_closed_constant_root_grammar_keeps_arithmetic_and_rejects_trailing_text():
    assert RationalParser(r"2\sqrt{3}x+\sqrt{12}").parse().value == 2 * sp.sqrt(
        3
    ) * X + 2 * sp.sqrt(3)
    with pytest.raises(UnsupportedCondition):
        RationalParser(r"2\sqrt{3}x unexpected").parse()
