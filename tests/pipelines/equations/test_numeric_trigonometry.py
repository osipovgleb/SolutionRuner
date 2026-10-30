"""Exact identities, periodic signs and original denominator domains."""

from fractions import Fraction
from itertools import product

import pytest
import sympy as sp

from solution_runner.pipelines.equations.trig_angles import parse_angle
from solution_runner.pipelines.equations.trig_numeric import calculate


def result(expression):
    return calculate(expression)[-1]


@pytest.mark.parametrize("theta,k", tuple(product([7, 19, 37, 62, 85], [-23, 1, 12])))
def test_complementary_functions_cancel_with_all_coefficient_signs(theta, k):
    assert (
        result(rf"\frac{{{k}\cos{theta}^{{\circ}}}}{{\sin{90 - theta}^{{\circ}}}}") == k
    )


@pytest.mark.parametrize(
    "theta,period", tuple(product([7, 19, 37, 62, 85], [-4, -1, 1, 5]))
)
def test_sine_period_and_reflection_preserve_the_exact_quotient(theta, period):
    assert (
        result(
            rf"\frac{{\sin({theta + 360 * period}^{{\circ}})}}{{\sin{theta}^{{\circ}}}}"
        )
        == 1
    )
    assert (
        result(
            rf"\frac{{\sin({360 * period - theta}^{{\circ}})}}{{\sin{theta}^{{\circ}}}}"
        )
        == -1
    )


@pytest.mark.parametrize("theta,k", tuple(product([7, 19, 37, 62, 85], [0, 1, 3])))
def test_sum_of_complementary_squares_is_checked_before_division(theta, k):
    assert result(
        rf"\frac{{7}}{{\cos^2{theta}^{{\circ}}+{k}+\cos^2{90 - theta}^{{\circ}}}}"
    ) == sp.Rational(7, k + 1)


@pytest.mark.parametrize("theta", [7, 19, 37, 62, 85])
def test_double_angle_products_and_quotients_reduce_exactly(theta):
    assert (
        result(
            rf"\frac{{12\sin{theta}^{{\circ}}\cos{theta}^{{\circ}}}}{{\sin{2 * theta}^{{\circ}}}}"
        )
        == 6
    )
    assert (
        result(
            rf"\frac{{12\sin{2 * theta}^{{\circ}}}}{{\sin{theta}^{{\circ}}\sin{90 - theta}^{{\circ}}}}"
        )
        == 24
    )
    assert (
        result(
            rf"\frac{{\sin{4 * theta}^{{\circ}}}}{{4\sin{theta}^{{\circ}}\cos{theta}^{{\circ}}\cos{2 * theta}^{{\circ}}}}"
        )
        == 1
    )


@pytest.mark.parametrize(
    "p,q,offset", tuple(product([-7, -1, 1, 5], [3, 4, 6], [-4, 0, 6]))
)
def test_radian_and_degree_encodings_give_the_same_tabular_value(p, q, offset):
    angle = sp.Rational(p, q) + offset
    # Square of the function removes the radical while retaining the period.
    expr = rf"4\sin^2(\frac{{{p}\pi}}{{{q}}}+{offset}\pi)"
    assert result(expr) == sp.simplify(4 * sp.sin(angle * sp.pi) ** 2)


@pytest.mark.parametrize(
    "angle,expected",
    [
        (r"30^{\circ}", Fraction(1, 6)),
        (r"(-750^{\circ})", Fraction(-25, 6)),
        (r"\frac{-27\pi}{4}", Fraction(-27, 4)),
        (r"2\pi", Fraction(2)),
        (r"(90-37)^{\circ}", Fraction(53, 180)),
    ],
)
def test_angle_units_are_explicit_and_never_rounded(angle, expected):
    assert parse_angle(angle)[0] == sp.Rational(
        expected.numerator, expected.denominator
    )


@pytest.mark.parametrize(
    "expression",
    [
        r"\tg90^{\circ}",
        r"0\cdot\tg90^{\circ}",
        r"\ctg0^{\circ}",
        r"\frac{\sin0^{\circ}}{\sin0^{\circ}}",
        r"\frac{1}{\sin^2 37^{\circ}+\cos^2 37^{\circ}-1}",
        r"\frac{0}{\cos^2 45^{\circ}-\sin^2 45^{\circ}}",
        r"\sin30",
        r"\sin(x)",
        r"\sin(30^{\circ})+",
        r"\sin(30^{\circ})+__import__(os)",
        r"\sin(11 2^{\circ})",
        r"\sin 37^{\circ}",
        r"\log_2 4+\sin30^{\circ}",
    ],
)
def test_undefined_poles_ambiguous_units_and_unsupported_values_fail_closed(expression):
    with pytest.raises(ValueError):
        result(expression)


def test_every_numeric_equation_in_prepared_solutions_is_an_exact_identity():
    import json
    import re
    from pathlib import Path

    from bs4 import BeautifulSoup
    from test_category_8_source_samples import CASES, plan

    from solution_runner.pipelines.equations.trig_angles import (
        C,
        S,
        choose_base,
        polynomial,
        reduce_polynomial,
    )
    from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

    groups = {
        g["key"]
        for g in json.loads(
            (Path(__file__).parent / "fixtures/category_8.json").read_text()
        )["groups"]
        if g["rule"] == "numeric-trigonometric-expression"
    }
    checked = 0
    for case in CASES:
        if case["group"] not in groups:
            continue
        result = plan(case, case["context"])
        html = next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        )
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
            text = tag["data-inline-latex"]
            if re.search("[a-zA-Z]", re.sub(r"\\[a-zA-Z]+", "", text)):
                continue
            pieces = text.split("=")
            atoms = {}
            try:
                nodes = [TrigonometricParser(p, atoms).parse() for p in pieces]
            except ValueError as exc:
                raise AssertionError((case["task"], text)) from exc
            if not atoms:
                assert all(n.value == nodes[0].value for n in nodes[1:])
                continue
            base = choose_base(list(atoms.values()))
            bindings = {
                symbol: polynomial(atom, base) for symbol, atom in atoms.items()
            }
            for node in nodes[1:]:
                difference = reduce_polynomial(
                    (node.value - nodes[0].value).xreplace(bindings)
                )
                if difference != 0 and base.q in [1, 2, 3, 4, 6, 8, 12]:
                    difference = sp.simplify(
                        difference.subs(
                            {S: sp.sin(base * sp.pi), C: sp.cos(base * sp.pi)}
                        )
                    )
                assert difference == 0, (case["task"], text, difference)
            checked += 1
    assert checked > 400
