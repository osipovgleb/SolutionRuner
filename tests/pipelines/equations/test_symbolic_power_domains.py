"""Independent identities and original-domain checks for the shared parsers."""

from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest
import sympy as sp
from test_category_8_source_samples import CASES, plan

from solution_runner.pipelines.equations.expression_repair import (
    repair_terminal_product,
)
from solution_runner.pipelines.equations.laurent_arithmetic import exact_value
from solution_runner.pipelines.equations.laurent_parser import LaurentParser
from solution_runner.pipelines.equations.power_expression import ledger_latex
from solution_runner.pipelines.equations.power_parser import PowerParser


@pytest.mark.parametrize("a,b", tuple(product([-3, -1, 2, 5], [-4, 1, 3])))
def test_integer_monomial_division_preserves_sign_and_exact_coefficients(a, b):
    parser = LaurentParser(r"\frac{(2a^{-2}b^3)^2}{4a^{-3}b^5}")
    poly = parser.parse()
    assert exact_value(
        poly, {"a": sp.Integer(a), "b": sp.Integer(b)}, parser.nonzero
    ) == Fraction(b, a)


def test_original_zero_denominator_is_rejected_after_total_cancellation():
    parser = LaurentParser(r"\frac{x^2}{x^2}")
    poly = parser.parse()
    assert exact_value(poly, {}, parser.nonzero) == 1
    with pytest.raises(ValueError, match="nonzero denominator"):
        exact_value(poly, {"x": sp.Integer(0)}, parser.nonzero)


def test_given_algebraic_values_can_cancel_to_an_exact_rational():
    parser = LaurentParser("a^2+b")
    assert (
        exact_value(
            parser.parse(), {"a": sp.sqrt(3), "b": -sp.Integer(2)}, parser.nonzero
        )
        == 1
    )


def test_explicit_division_consumes_the_entire_following_monomial():
    parser = LaurentParser(r"8x^3\colon4x^2")
    assert exact_value(parser.parse(), {"x": sp.Integer(-3)}, parser.nonzero) == -6


def test_symbol_substitution_does_not_replace_letters_inside_latex_commands():
    terms = PowerParser(r"a^{\frac{1}{2}}", {"a"}).parse()
    rendered = ledger_latex(terms, simplified=True, bindings={"a": sp.Integer(9)})
    assert rendered == r"(9)^{\frac{1}{2}}"
    terms = PowerParser("2^{a+1}", {"a"}).parse()
    assert (
        ledger_latex(terms, simplified=True, bindings={"a": sp.Integer(2)}) == "2^{3}"
    )


@pytest.mark.parametrize("task", ["519805", "65795", "502066"])
def test_terminal_operator_repair_requires_the_matching_source_expression(task):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    prepared, change = repair_terminal_product(context)
    assert prepared != context and change["transformation_target_id"].startswith(
        "section:condition"
    )
    assert repair_terminal_product(prepared)[1] is None
    for section in context["normalized_content"]["sections"]:
        if section["key"] == "solution":
            section["html"] = '<p><span data-inline-latex="1=1"></span></p>'
    with pytest.raises(ValueError, match="not confirmed"):
        repair_terminal_product(context)


def test_wrong_saved_answer_is_corrected_using_an_independent_identity():
    case = next(c for c in CASES if c["task"] == "89487")
    assert Fraction(2 * 4**4, 2**10) == Fraction(1, 2)
    assert plan(case, deepcopy(case["context"])).answer == "0,5"
