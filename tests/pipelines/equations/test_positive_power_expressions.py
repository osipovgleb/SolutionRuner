"""Independent exact identities exercise the positive-base power grammar."""

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import product

import pytest
import sympy as sp
from test_category_8_source_samples import CASES, plan

from solution_runner.pipelines.core.numbers import format_answer, format_latex_fraction
from solution_runner.pipelines.equations.power_arithmetic import (
    ScalarParser,
    exact_value,
)
from solution_runner.pipelines.equations.power_expression import _three_methods
from solution_runner.pipelines.equations.power_parser import PowerParser


def value(expression, bindings=None):
    bindings = bindings or {}
    return exact_value(PowerParser(expression, bindings).parse(), bindings)[0]


@pytest.mark.parametrize(
    "base,k,v,n", tuple(product([2, 3, 6], [2, 3], [F(1, 3), F(-2, 5)], [-1, 0, 2]))
)
def test_related_bases_reduce_to_the_independently_chosen_integer_power(base, k, v, n):
    u = F(n) - k * v
    expression = rf"{base}^{{{format_latex_fraction(u)}}}\cdot{base**k}^{{{format_latex_fraction(v)}}}"
    assert value(expression) == F(base) ** n


@pytest.mark.parametrize("base,d,q", tuple(product([2, 5], [2, 5, 8], [-1, 2])))
def test_square_root_exponents_cancel_exactly_across_a_quotient(base, d, q):
    expression = (
        rf"\frac{{{base**2}^{{\sqrt{{{d}}}{q:+d}}}}}{{{base}^{{2\sqrt{{{d}}}}}}}"
    )
    assert value(expression) == F(base) ** (2 * q)


@pytest.mark.parametrize(
    "base,degree", tuple(product([F(2), F(3, 5), F(7, 4)], [2, 3, 5]))
)
def test_positive_roots_and_integer_powers_are_inverse_operations(base, degree):
    expression = rf"\sqrt[{degree}]{{({format_latex_fraction(base)})^{{{degree}}}}}"
    assert value(expression) == base


@pytest.mark.parametrize(
    "expression",
    [
        r"0^{0}",
        r"(-2)^{2}",
        r"2^{\sqrt{2}}",
        r"\frac{1}{0}",
        r"2^{\frac{1}{0}}",
        r"\sqrt[1]{2}",
        r"\sqrt[101]{2}",
        r"2^{3}+1",
        r"2^{3}\cdot",
        r"2 3",
        r"10000000000^{1}",
        r"\log_{2}8",
        r"2^{__import__(os)}",
    ],
)
def test_unsupported_domains_or_incomplete_syntax_fail_closed(expression):
    with pytest.raises(ValueError):
        value(expression)


def test_rational_decimal_and_radical_exponents_are_never_rounded():
    assert ScalarParser(r"3\sqrt{8}-6\sqrt{2}+0{,}125").parse() == sp.Rational(1, 8)
    assert value(r"\frac{5^{\sqrt{6}-3}}{0{,}2^{-\sqrt{6}}}") == F(1, 125)


@pytest.mark.parametrize(
    "q,a,b", [(3, F(4, 5), 5), (7, F(4, 5), 5), (8, F(3, 5), 5), (8, F(3, 4), 4)]
)
def test_all_three_source_methods_follow_the_same_base_relation(q, a, b):
    c = a * b * b

    def base(v):
        return format_answer(F(v)).replace(",", "{,}")

    expression = rf"{base(a)}^{{\frac{{1}}{{{q}}}}}\cdot{base(b)}^{{\frac{{2}}{{{q}}}}}\cdot{base(c)}^{{\frac{{{q - 1}}}{{{q}}}}}"
    terms = PowerParser(expression).parse()
    answer, html = _three_methods(expression, terms)
    assert answer == c
    assert (
        html.index("Первый способ")
        < html.index("Второй способ")
        < html.index("Третий способ")
    )
    assert rf"\sqrt[{q}]" in html


def test_a_different_third_base_cannot_use_the_three_source_methods():
    expression = r"0{,}8^{\frac{1}{7}}\cdot5^{\frac{2}{7}}\cdot21^{\frac{6}{7}}"
    with pytest.raises(ValueError, match="base relation"):
        _three_methods(expression, PowerParser(expression).parse())


def test_wrong_zero_answers_are_verified_independently():
    for task, expected in [("62117", "12"), ("14679", "196")]:
        case = next(c for c in CASES if c["task"] == task)
        result = plan(case, deepcopy(case["context"]))
        assert result.answer == expected
        assert any(
            t["transformation_target_id"].startswith("section:answer")
            for t in result.transformations
        )
    assert F(4**7 * 49**7, 196**6) == 196
    with localcontext() as ctx:
        ctx.prec = 70
        decimal_value = (
            Decimal(12) ** (Decimal(16) / 5)
            * Decimal(6) ** (-Decimal(11) / 5)
            / Decimal(2) ** (Decimal(11) / 5)
        )
        assert abs(decimal_value - 12) < Decimal("1e-50")
