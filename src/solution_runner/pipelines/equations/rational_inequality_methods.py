"""Parent-specific algebra over one shared rational interval calculation."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_parser import X, polynomial


@dataclass(frozen=True)
class Step:
    text: str
    value: sp.Expr


def latex(value):
    return sp.latex(value, mul_symbol=None)


def fraction(numerator, denominator):
    return r"\frac{" + latex(numerator) + "}{" + latex(denominator) + "}"


def terms(node, sign=1):
    if node.kind in ("add", "subtract"):
        return terms(node.children[0], sign) + terms(
            node.children[1], -sign if node.kind == "subtract" else sign
        )
    if node.kind == "negative":
        return terms(node.children[0], -sign)
    return [(sign, node)]


def divisions(node):
    result = []
    for sign, term in terms(node):
        if term.kind != "divide":
            raise UnsupportedCondition(
                "the parent method requires a sum of explicit fractions"
            )
        numerator, denominator = (c.value for c in term.children)
        polynomial(numerator)
        polynomial(denominator)
        result.append((sign * numerator, denominator))
    return result


def sum_fractions(a):
    values = divisions(a.left)
    if (
        a.right.value != 0
        or len(values) != 3
        or any(
            polynomial(n).degree() > 0 or polynomial(d).degree() != 1 for n, d in values
        )
    ):
        raise UnsupportedCondition("three constant-over-affine fractions are required")
    denominator = sp.lcm([d for _, d in values])
    pieces = [
        sp.Mul(n, sp.expand(sp.cancel(denominator / d)), evaluate=False)
        for n, d in values
    ]
    numerator = sp.Add(*pieces, evaluate=False)
    return [], [
        Step(fraction(numerator, sp.factor(denominator)), a.original),
        Step(fraction(sp.expand(numerator), sp.factor(denominator)), a.original),
    ]


def direct_fraction(a):
    values = divisions(a.left)
    if (
        a.right.value != 0
        or len(values) != 1
        or any(polynomial(p).degree() != 2 for p in values[0])
    ):
        raise UnsupportedCondition("one quadratic-over-quadratic fraction is required")
    numerator, denominator = values[0]
    return [], [
        Step(fraction(sp.factor(numerator), sp.factor(denominator)), a.original)
    ]


def cancelled_fraction(a):
    items = terms(a.left)
    if (
        len(items) != 3
        or items[0][0] != 1
        or items[0][1].value != X
        or a.right.value != 1
        or len(a.holes) != 1
    ):
        raise UnsupportedCondition(
            "the parent method requires x, two fractions and one cancelled hole"
        )
    values = []
    for sign, item in items[1:]:
        if item.kind != "divide":
            raise UnsupportedCondition("two original fractions are required")
        n, d = (c.value for c in item.children)
        values.append((sign * n, d))
    (n, d), (last, common) = values
    if [polynomial(v).degree() for v in (n, d, last, common)] != [1, 1, 2, 2]:
        raise UnsupportedCondition("affine and quadratic fractions are required")
    multiplier = sp.cancel(common / d)
    corrected = sp.expand(last - common)
    if not multiplier.is_polynomial(X) or polynomial(corrected).degree() > 1:
        raise UnsupportedCondition(
            "subtracting one must leave an affine last numerator"
        )
    combined = sp.expand(n * multiplier + corrected)
    numerator = sp.Add(X * sp.factor(common), combined, evaluate=False)
    factored = sp.Add(X * sp.factor(common), sp.factor(combined), evaluate=False)
    value = X + n / d + corrected / common
    first = "x+" + fraction(n, d) + "+" + fraction(corrected, sp.factor(common))
    return [], [
        Step(first, value),
        Step(fraction(numerator, sp.factor(common)), value),
        Step(fraction(factored, sp.factor(common)), value),
    ]


def long_division(a):
    values = divisions(a.left)
    if len(values) != 2 or any(
        polynomial(n).degree() > 2 or polynomial(d).degree() != 1 for n, d in values
    ):
        raise UnsupportedCondition("two polynomial-over-affine fractions are required")
    quotients, remainders, identities = [], [], []
    for numerator, denominator in values:
        quotient, remainder = sp.div(numerator, denominator, X)
        if polynomial(remainder).degree() > 0:
            raise UnsupportedCondition("the division remainder must be constant")
        quotients.append(quotient)
        remainders.append(remainder / denominator)
        expanded = sp.Add(
            sp.Mul(quotient, denominator, evaluate=False), remainder, evaluate=False
        )
        identities.append(
            (
                latex(numerator) + "=" + latex(expanded),
                numerator,
                denominator * quotient + remainder,
            )
        )
    if sp.expand(sum(quotients) - a.right.value) != 0:
        raise UnsupportedCondition(
            "the polynomial quotients must cancel the right side"
        )
    residual = sp.Add(*remainders, evaluate=False)
    return identities, [Step(latex(residual), residual)]


def factor_cancelled(a):
    values = divisions(a.left)
    if a.right.value != 0 or len(values) != 2:
        raise UnsupportedCondition(
            "two fractions with a common numerator factor are required"
        )
    (first, affine), (second, denominator) = values
    if [polynomial(v).degree() for v in (first, affine, second, denominator)] != [
        2,
        1,
        1,
        2,
    ]:
        raise UnsupportedCondition("quadratic and affine source factors are required")
    other = sp.cancel(denominator / affine)
    common = -second
    if (
        not other.is_polynomial(X)
        or polynomial(other).degree() != 1
        or sp.expand(first - common * other) != 0
    ):
        raise UnsupportedCondition(
            "the two fractions must yield the reviewed difference of squares"
        )
    factored_first = sp.Mul(common, other, evaluate=False)
    factored_denominator = sp.factor(denominator)
    first_text = (
        fraction(factored_first, affine) + "-" + fraction(common, factored_denominator)
    )
    expanded_text = (
        r"\frac{"
        + latex(sp.Mul(common, other**2, evaluate=False))
        + "-("
        + latex(common)
        + ")}{"
        + latex(factored_denominator)
        + "}"
    )
    factored = sp.Mul(other**2 - 1, common, evaluate=False)
    return [], [
        Step(first_text, a.original),
        Step(expanded_text, a.original),
        Step(fraction(factored, factored_denominator), a.original),
        Step(
            fraction(sp.factor(sp.expand(factored)), factored_denominator), a.original
        ),
    ]


def square_numerator(a):
    values = divisions(a.left)
    if len(values) != 1 or a.right.value.free_symbols:
        raise UnsupportedCondition("one fraction and a scalar right side are required")
    numerator, denominator = values[0]
    if polynomial(numerator).degree() != 2 or polynomial(denominator).degree() != 1:
        raise UnsupportedCondition(
            "a quadratic-over-affine source fraction is required"
        )
    corrected = sp.expand(numerator - a.right.value * denominator)
    p = polynomial(corrected)
    if p.degree() != 2 or sp.discriminant(p) != 0:
        raise UnsupportedCondition(
            "subtracting the right side must leave a perfect square"
        )
    combined = sp.Add(
        numerator, sp.Mul(-a.right.value, denominator, evaluate=False), evaluate=False
    )
    return [], [
        Step(fraction(combined, denominator), a.original),
        Step(fraction(corrected, denominator), a.original),
    ]


def prepare(a, method):
    from .rational_inequality_algebraic_methods import METHODS, presentation
    from .rational_inequality_polynomial_methods import METHODS as POLYNOMIAL_METHODS

    a = presentation(a, method)
    operation = {
        "long_division": long_division,
        "sum_fractions": sum_fractions,
        "cancelled_fraction": cancelled_fraction,
        "direct_fraction": direct_fraction,
        "factor_cancelled": factor_cancelled,
        "square_numerator": square_numerator,
        **METHODS,
        **POLYNOMIAL_METHODS,
    }.get(method)
    if operation is None:
        raise UnsupportedCondition("unknown reviewed rational inequality method")
    identities, steps = operation(a)
    if any(sp.cancel(step.value - a.original) != 0 for step in steps) or any(
        sp.expand(left - right) != 0 for _, left, right in identities
    ):
        raise UnsupportedCondition(
            "the parent-method identities must match the complete condition"
        )
    return identities, steps
