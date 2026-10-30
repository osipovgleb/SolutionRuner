"""Exact radicals, angle signs and inverse-length identifiability."""

import pytest
import sympy as sp

from solution_runner.pipelines.vectors.metric_relations import (
    cosine,
    measure,
    metric_value,
)


@pytest.mark.parametrize(
    "angle,expected",
    [
        (0, sp.Integer(1)),
        (30, sp.sqrt(3) / 2),
        (45, sp.sqrt(2) / 2),
        (60, sp.Rational(1, 2)),
        (90, sp.Integer(0)),
        (120, -sp.Rational(1, 2)),
        (135, -sp.sqrt(2) / 2),
        (150, -sp.sqrt(3) / 2),
        (180, sp.Integer(-1)),
    ],
)
def test_degree_conversion_and_dot_product_signs(angle, expected):
    assert cosine(angle) == expected
    a, b = measure(r"3\sqrt{2}"), measure(r"5\sqrt{3}")
    actual = metric_value(a, b, angle)
    assert sp.simplify(actual - a * b * expected) == 0
    if angle != 90:
        assert sp.simplify(metric_value(a, actual, angle, inverse=True) - b) == 0


@pytest.mark.parametrize(
    "text,expected",
    [
        (r"2\sqrt{3}", 2 * sp.sqrt(3)),
        (r"\frac{3}{2}\sqrt{8}", 3 * sp.sqrt(2)),
        ("2{,}5", sp.Rational(5, 2)),
        ("−28", sp.Integer(-28)),
        (r"-\sqrt{2}", -sp.sqrt(2)),
    ],
)
def test_strict_radical_measurements_are_exact(text, expected):
    assert sp.simplify(measure(text) - expected) == 0


@pytest.mark.parametrize(
    "text",
    [
        '__import__("os")',
        r"\sqrt{-2}",
        r"\sqrt{x}",
        r"2+3",
        r"\sin{45}",
        "",
        r"\frac{1}{0}",
    ],
)
def test_unsupported_measurement_syntax_is_never_evaluated(text):
    with pytest.raises(ValueError):
        measure(text)


@pytest.mark.parametrize(
    "angle,product", [(90, 0), (90, 1), (45, -2), (135, 2), (45, 0)]
)
def test_unknown_length_needs_a_nonzero_cosine_and_consistent_sign(angle, product):
    with pytest.raises(ValueError):
        metric_value(sp.Integer(2), sp.Integer(product), angle, inverse=True)


@pytest.mark.parametrize("angle", [-1, 181, 360])
def test_angle_range_is_validated(angle):
    with pytest.raises(ValueError):
        cosine(angle)


def test_zero_or_negative_lengths_do_not_define_the_given_angle():
    assert metric_value(sp.Integer(2), sp.Integer(3), 90) == 0
    with pytest.raises(ValueError):
        metric_value(sp.Integer(0), sp.Integer(3), 45)
    with pytest.raises(ValueError):
        metric_value(sp.Integer(2), sp.Integer(-3), 45)
