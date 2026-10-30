"""Vector identities, exact decimals and rejected undefined scalar operations."""

from copy import deepcopy
from fractions import Fraction as F
from itertools import product

import pytest
from test_coordinate_source_samples import CASES, plan

from solution_runner.pipelines.vectors.coordinates import evaluate, exact_root

VECTORS = [(F(-3, 2), F(5)), (F(0), F(0)), (F(7), F(-2))]


@pytest.mark.parametrize("a,b,c", tuple(product(VECTORS, repeat=3)))
def test_dot_distributivity_and_norm_polarization(a, b, c):
    env = {"a": a, "b": b, "c": c}
    left, _ = evaluate(r"\vec{a}\cdot(\vec{b}+\vec{c})", env)
    right, _ = evaluate(r"\vec{a}\cdot\vec{b}+\vec{a}\cdot\vec{c}", env)
    assert left == right == sum(x * (y + z) for x, y, z in zip(a, b, c, strict=True))
    result, _ = evaluate(r"(\vec{a}+\vec{b})\cdot(\vec{a}+\vec{b})", env)
    dot, _ = evaluate(r"\vec{a}\cdot\vec{b}", env)
    assert result == sum(x * x for x in a) + 2 * dot + sum(x * x for x in b)


def test_decimal_coefficients_are_exact():
    value, _ = evaluate(
        r"1{,}2\vec{a}-0{,}7\vec{b}", {"a": (F(3), F(7)), "b": (F(8), F(9))}
    )
    assert value == (F(-2), F(21, 10))
    assert exact_root(sum(x * x for x in value)) == F(29, 10)
    negative, _ = evaluate(
        r"-\frac{3}{2}(\vec{a}-\vec{b})", {"a": (F(2), F(1)), "b": (F(4), F(3))}
    )
    assert negative == (F(3), F(3))


@pytest.mark.parametrize(
    "expression",
    [
        r"\vec{z}",
        r"\sin(\vec{a})",
        '__import__("os")',
        r"\vec{a}/2",
        r"1+\vec{a}",
        r"2 3\vec{a}",
        r"(\vec{a}+\vec{b}",
        r"\vec{a})",
    ],
)
def test_unknown_or_ill_typed_expressions_fail_closed(expression):
    with pytest.raises(ValueError):
        evaluate(expression, {"a": (F(1), F(2)), "b": (F(2), F(3))})


def test_zero_vector_has_length_but_no_mutual_angle():
    case = next(c for c in CASES if c["group"] == "649915")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        r'<p>Даны векторы <span data-inline-latex="\vec{a}(0;0)"></span> и <span data-inline-latex="\vec{b}(3;4)"></span>. Найдите косинус угла между ними.</p>'
    )
    with pytest.raises(ValueError):
        plan(case, context)
    assert exact_root(F(0)) == 0
    with pytest.raises(ValueError):
        exact_root(F(2))
