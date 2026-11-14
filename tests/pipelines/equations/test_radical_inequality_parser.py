"""Typed roots preserve the original domain even when symbolic factors cancel."""

import json
import re
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.equations.radical_inequality_comparison import analyze
from solution_runner.pipelines.equations.radical_inequality_parser import RadicalParser
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("radical_inequality_sources.json")
    .read_text()
)


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["task"])
def test_complete_original_formulas_have_typed_roots_and_retained_denominators(row):
    formula = read_formula(row["context"])[1]
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", formula)
    assert len(parts) == 3
    roots, denominators = {}, []
    nodes = [
        RadicalParser(part, denominators, radicands=roots).parse()
        for part in (parts[0], parts[2])
    ]
    assert 1 <= len(roots) <= 3
    assert denominators
    assert all(node.value.free_symbols <= {X, *roots} for node in nodes)
    assert all(value.is_polynomial(X) for value in roots.values())


def test_shared_root_identity_does_not_remove_original_radical_pole():
    parser = RadicalParser(r"\frac{\sqrt{x+1}-1}{\sqrt{1+x}-1}")
    node = parser.parse()
    assert node.value == 1
    assert len(parser.radicands) == 1
    symbol = next(iter(parser.radicands))
    assert parser.denominators == [symbol - 1]
    assert node.kind == "divide"
    assert node.children[0].kind == "subtract"


def test_rational_hole_inside_radicand_survives_cancellation():
    parser = RadicalParser(r"\sqrt{\frac{x}{x}+x}")
    parser.parse()
    assert tuple(parser.radicands.values()) == (X + 1,)
    assert parser.denominators == [X]


def test_cancelled_external_hole_and_nonpositive_root_power_are_retained():
    parser = RadicalParser(r"\frac{x-3}{x-3}(\sqrt{6*x-x^2})^{-2}")
    node = parser.parse()
    symbol = next(iter(parser.radicands))
    assert node.value == symbol**-2
    assert parser.denominators == [X - 3, symbol]


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{x^4+1}",
        r"\sqrt{\sqrt{x}+1}",
        r"\sqrt{1/x}",
        r"\sqrt{-1}",
        r"\sqrt{x}+y",
        r"\sqrt{x}+root",
        r"\sqrt{x}+\sqrt{x+1}+\sqrt{x+2}+\sqrt{x+3}",
        r"(\sqrt{x})^{9}",
        r"\frac{\sqrt{x}}{0}",
        r"\sqrt{x} trailing",
    ],
)
def test_unknown_or_unbounded_root_syntax_is_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        RadicalParser(formula).parse()


def test_ordinary_rational_parser_still_rejects_variable_roots():
    with pytest.raises(UnsupportedCondition):
        RationalParser(r"\sqrt{x+1}").parse()
    assert RationalParser(r"\sqrt{5}+x").parse().value == X + sp.sqrt(5)


@pytest.mark.parametrize(
    "task,left,numerator,denominator,expected",
    [
        (
            "507612",
            7 - X,
            X**3 - 6 * X**2 + 14 * X - 7,
            X - 1,
            sp.Union(sp.Interval.open(1, 2), sp.Interval.Lopen(3, 7)),
        ),
        (
            "507833",
            5 - X,
            X**3 - 7 * X**2 + 14 * X - 5,
            X - 1,
            sp.Union(sp.Interval.open(1, 2), sp.Interval.Lopen(4, 5)),
        ),
        (
            "511449",
            6 - X,
            X**3 - 7 * X**2 + 13 * X + 6,
            X + 1,
            sp.Union(sp.Interval.open(0, 2), sp.Interval.Lopen(4, 6)),
        ),
    ],
)
def test_three_root_source_answers_and_original_values(
    task, left, numerator, denominator, expected
):
    row = next(row for row in ROWS if row["task"] == task)
    result = analyze(read_formula(row["context"])[1])
    assert (result.left, result.numerator, result.denominator) == (
        left,
        numerator,
        denominator,
    )
    assert result.solution == expected
    for sample in (sp.Rational(n, 4) for n in range(-12, 33)):
        a, b, c = (value.subs(X, sample) for value in (left, denominator, numerator))
        valid = a >= 0 and b > 0 and c >= 0
        actual = bool(sp.sqrt(a) < sp.sqrt(c) / sp.sqrt(b)) if valid else False
        assert bool(result.solution.contains(sample)) == actual


def test_cubic_domain_is_redundant_only_after_strict_stage():
    row = next(row for row in ROWS if row["task"] == "511449")
    result = analyze(read_formula(row["context"])[1])
    assert result.domain.contains(-sp.Rational(1, 2))
    assert result.numerator.subs(X, -sp.Rational(1, 2)) < 0
    assert not result.solution.contains(-sp.Rational(1, 2))
    assert result.solution.contains(6)
    assert not result.solution.contains(0)


def test_cancelled_pole_inside_a_root_stays_out_of_the_three_root_solution():
    result = analyze(
        r"\sqrt{\frac{2*x-3}{2*x-3}+6-x}<"
        r"\frac{\sqrt{x^3-6*x^2+14*x-7}}{\sqrt{x-1}}"
    )
    assert result.poles == (sp.Rational(3, 2),)
    assert not result.solution.contains(sp.Rational(3, 2))
    assert result.solution.contains(sp.Rational(5, 4))


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{7-x}<\sqrt{x^3-6*x^2+14*x-7}",
        r"\sqrt{7-x}+1<\frac{\sqrt{x^3-6*x^2+14*x-7}}{\sqrt{x-1}}",
        r"\sqrt{7-x}<\frac{\sqrt{x^3-6*x^2+14*x-7}}{1+\sqrt{x-1}}",
        r"\sqrt{7-x}<\frac{\sqrt{x^2+1}}{\sqrt{x-1}}",
        r"\sqrt{7-x}<\frac{\sqrt{x^3+1}}{\sqrt{x^2+1}}",
    ],
)
def test_three_root_method_rejects_unreviewed_shapes(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize("operator", [">", r"\le", r"\ge", "="])
def test_three_root_redundancy_is_not_used_for_other_comparisons(operator):
    formula = r"\sqrt{7-x}" + operator + r"\frac{\sqrt{x^3-6*x^2+14*x-7}}{\sqrt{x-1}}"
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
