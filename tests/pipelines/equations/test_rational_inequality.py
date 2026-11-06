"""Independent native-answer and original-domain checks for interval analysis."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.equations.rational_inequality import analyze, set_latex
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_inequality_sources.json")
    .read_text()
)


def endpoint(text):
    text = text.strip()
    if text in (r"-\infty", r"\infty", r"+\infty"):
        return -sp.oo if text.startswith("-") else sp.oo
    return ScalarParser(text).parse()


def answer_set(text):
    intervals = []
    for item in text.strip().removesuffix(".").split(r"\cup"):
        item = item.strip()
        if item.startswith(r"\{") and item.endswith(r"\}"):
            intervals.append(sp.FiniteSet(*map(endpoint, item[2:-2].split(";"))))
            continue
        left, right = map(endpoint, item[1:-1].split(";"))
        intervals.append(
            sp.Interval(
                left, right, left_open=item[0] == "(", right_open=item[-1] == ")"
            )
        )
    return sp.Union(*intervals)


@pytest.mark.parametrize("row", SOURCES, ids=lambda row: row["task"])
def test_native_answer_and_independent_cas(row):
    condition = next(
        s
        for s in row["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    formula = BeautifulSoup(condition["html"], "html.parser").find(
        "span", attrs={"data-inline-latex": True}
    )["data-inline-latex"]
    a = analyze(formula.removesuffix("."))
    expected = answer_set(row["expected_answer"])
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    )
    independent -= sp.FiniteSet(*a.poles)
    assert a.solution == independent == expected
    assert answer_set(set_latex(a.solution)) == expected


@pytest.mark.parametrize(
    "formula,expected",
    [
        (
            r"\frac{(x-1)(x-2)}{x-1}\le 0",
            sp.Interval.open(-sp.oo, 1) | sp.Interval.Lopen(1, 2),
        ),
        (r"\frac{(x-1)^2}{(x-1)^2}\ge 0", sp.S.Reals - sp.FiniteSet(1)),
        (r"\frac{(x-1)^2}{x+2}\le 0", sp.Interval.open(-sp.oo, -2) | sp.FiniteSet(1)),
        (r"\frac{(x-1)^2}{x+2}<0", sp.Interval.open(-sp.oo, -2)),
        (r"\frac{1}{x-1}-\frac{1}{x-1}\ge 0", sp.S.Reals - sp.FiniteSet(1)),
        (r"\frac{1}{x-1}-\frac{1}{x-1}>0", sp.EmptySet),
        (r"\frac{1}{\frac{1}{x-1}}\ge 0", sp.Interval.open(1, sp.oo)),
        (r"(x-1)^{-2}\ge 0", sp.S.Reals - sp.FiniteSet(1)),
        (
            r"-\frac{2(x-1)}{3(x+1)}\le 0",
            sp.Interval.open(-sp.oo, -1) | sp.Interval(1, sp.oo),
        ),
        (r"\frac{x-1}{x-1}\le 0", sp.EmptySet),
        (r"(x-1)^0\ge 0", sp.S.Reals - sp.FiniteSet(1)),
        (r"\frac{x^0}{x+1}>0", sp.Interval.open(-1, 0) | sp.Interval.open(0, sp.oo)),
        (r"\frac{1}{(x-2)^0}\le 1", sp.S.Reals - sp.FiniteSet(2)),
    ],
)
def test_cancellation_multiplicity_strictness_and_negative_normalization(
    formula, expected
):
    assert analyze(formula).solution == expected


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{x}\le 0",
        r"\sin(x)>0",
        r"\log_2(x)>0",
        "y>0",
        "x<x<2",
        r"x^{1000}>0",
        r"x^x>0",
        r"\frac{1}{x-x}>0",
        r"\frac{x}{0}>0",
        r"x=0",
        r"x>0\text{или}x<0",
        "__import__('os')>0",
        r"(x+1)^8(x+2)^8>0",
        "999999999999999999x>0",
        "x>0 extra",
    ],
)
def test_unknown_or_unbounded_condition_is_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_parser_preserves_original_division_tree_and_domain():
    reader = RationalParser(r"\frac{x^2-1}{x-1}+\frac{1}{x+2}")
    node = reader.parse()
    assert node.kind == "add"
    assert node.children[0].kind == "divide"
    assert reader.denominators == [X - 1, X + 2]
    assert sp.cancel(node.value - (X + 1 + 1 / (X + 2))) == 0


def test_linear_numerator_after_quadratic_terms_cancel():
    a = analyze(r"\frac{1}{x}+\frac{1}{x+1}-\frac{2}{x+2}\ge 0")
    assert a.zeros == (-sp.Rational(2, 3),)
    assert a.sign_operator == ">="


METHODS = {
    "508440": "sum_fractions",
    "508518": "cancelled_fraction",
    "508524": "direct_fraction",
    "511560": "long_division",
    "507491": "factor_cancelled",
    "508404": "square_numerator",
    "508299": "opposite_fractions",
    "508442": "vieta_quadratic",
    "556602": "cancelled_quadratic_sum",
}


@pytest.mark.parametrize("row", SOURCES, ids=lambda row: row["task"])
def test_parent_method_every_printed_identity_and_reduced_inequality(row):
    from solution_runner.pipelines.equations.rational_inequality_algebraic_methods import (
        presentation,
    )
    from solution_runner.pipelines.equations.rational_inequality_methods import prepare
    from solution_runner.pipelines.equations.rational_inequality_proof import render

    condition = next(
        s
        for s in row["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    formula = BeautifulSoup(condition["html"], "html.parser").find(
        "span", attrs={"data-inline-latex": True}
    )["data-inline-latex"]
    a = analyze(formula.removesuffix("."))
    method = METHODS[row["group"]]
    a = presentation(a, method)
    identities, steps = prepare(a, method)
    for text, expected_left, expected_right in identities:
        left, right = [RationalParser(part).parse().value for part in text.split("=")]
        assert sp.cancel(left - expected_left) == sp.cancel(right - expected_right) == 0
    for step in steps:
        assert sp.cancel(RationalParser(step.text).parse().value - a.original) == 0
    html = render(a, method)
    assert formula.removesuffix(".") in [
        span["data-inline-latex"]
        for span in BeautifulSoup(html, "html.parser").find_all(
            "span", attrs={"data-inline-latex": True}
        )
    ]
    assert set_latex(a.solution) in html
    if a.holes:
        assert "Сокращение общего множителя сохраняет" in html
    if method == "long_division":
        assert "положительный множитель" in html


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{1}{x-1}>0", "sum_fractions"),
        (r"\frac{x}{x-1}>0", "direct_fraction"),
        (r"x+\frac{1}{x-1}+\frac{1}{x^2-1}>1", "cancelled_fraction"),
        (r"\frac{x+1}{x-1}+\frac{x+2}{x-2}>3", "long_division"),
    ],
)
def test_parent_method_does_not_silently_switch_to_generic_solver(formula, method):
    from solution_runner.pipelines.equations.rational_inequality_methods import prepare

    with pytest.raises(UnsupportedCondition):
        prepare(analyze(formula), method)


@pytest.mark.parametrize(
    "formula,method,expected",
    [
        (
            r"\frac{x^2-8x+15}{x-1}-\frac{x-5}{x^2-4x+3}\le0",
            "factor_cancelled",
            r"(-\infty;1)\cup [2;3)\cup [4;5]",
        ),
        (
            r"\frac{x^2-3x+2}{x-1}-\frac{x-1}{x^2-3x+2}\le0",
            "factor_cancelled",
            r"(-\infty;1)\cup (2;3]",
        ),
        (
            r"\frac{3x^2-6x+9}{2x-1}\le3",
            "square_numerator",
            r"(-\infty;\frac{1}{2})\cup\{2\}",
        ),
        (r"\frac{-x^2-2x-10}{x-3}\le2", "square_numerator", r"\{-2\}\cup(3;\infty)"),
    ],
)
def test_method_expansion_respects_changed_factors_and_coincident_original_pole(
    formula, method, expected
):
    from solution_runner.pipelines.equations.rational_inequality_methods import prepare

    a = analyze(formula)
    _, steps = prepare(a, method)
    assert a.solution == answer_set(expected)
    for step in steps:
        assert sp.cancel(RationalParser(step.text).parse().value - a.original) == 0


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{x^2-6x+9}{x-1}-\frac{x-4}{x^2-3x+2}\le0", "factor_cancelled"),
        (r"\frac{x^2+1}{x-1}\le2", "square_numerator"),
        (r"\frac{x^2+1}{x-1}\le x", "square_numerator"),
    ],
)
def test_new_parent_algebra_rejects_an_unproved_common_factor_or_square(
    formula, method
):
    from solution_runner.pipelines.equations.rational_inequality_methods import prepare

    with pytest.raises(UnsupportedCondition):
        prepare(analyze(formula), method)
