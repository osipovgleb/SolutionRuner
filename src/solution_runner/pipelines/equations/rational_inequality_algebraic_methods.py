"""Reviewed common-denominator, Vieta and cancellation methods with exact surds."""

from dataclasses import replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality import FLIPPED, interval_signs
from .rational_inequality_methods import Step, divisions, fraction, latex, terms
from .rational_inequality_parser import X, polynomial


def original_orientation(a):
    signs, solution = interval_signs(a.original, a.points, a.operator, a.poles)
    if solution != a.solution:
        raise UnsupportedCondition(
            "the source sign orientation must preserve the solution"
        )
    return replace(a, expression=a.original, sign_operator=a.operator, signs=signs)


def presentation(a, method):
    if method not in METHODS and method != "degree_division":
        return a
    if a.presentation_method:
        if a.presentation_method != method:
            raise UnsupportedCondition(
                "the reviewed presentation method must stay fixed"
            )
        return a
    if method == "opposite_fractions":
        return replace(original_orientation(a), presentation_method=method)
    if method == "degree_division":
        numerator, denominator = sp.fraction(a.original)
        content = sp.Abs(
            polynomial(numerator).content() / polynomial(denominator).content()
        )
        expression = sp.cancel(a.original / content)
        signs, solution = interval_signs(expression, a.points, a.operator, a.poles)
        if solution != a.solution:
            raise UnsupportedCondition(
                "the source sign orientation must preserve the answer"
            )
        return replace(
            a,
            expression=expression,
            sign_operator=a.operator,
            signs=signs,
            presentation_method=method,
        )
    if method == "cancelled_quadratic_sum":
        return replace(
            a,
            left=a.right,
            right=a.left,
            original=-a.original,
            operator=FLIPPED[a.operator],
            presentation_method=method,
        )
    return replace(a, presentation_method=method)


def real_factor(value, zeros):
    p = polynomial(value)
    factors = []
    for root in zeros:
        current = p
        while current.degree() > 0 and sp.simplify(current.eval(root)) == 0:
            quotient, remainder = sp.div(current.as_expr(), X - root, X)
            if sp.simplify(remainder) != 0:
                raise UnsupportedCondition(
                    "each displayed linear factor must divide exactly"
                )
            factors.append(X - sp.factor_terms(root))
            current = sp.Poly(sp.simplify(quotient), X)
        p = current
    if p.degree() != 0:
        raise UnsupportedCondition(
            "this parent factorization needs all real quadratic roots"
        )
    return sp.Mul(
        *(([p.as_expr()] if p.as_expr() != 1 else []) + factors), evaluate=False
    )


def opposite_fractions(a):
    values = divisions(a.left)
    if len(values) != 2 or a.right.value.free_symbols or a.right.value <= 0:
        raise UnsupportedCondition(
            "two positive constant fractions and a positive bound are required"
        )
    (first, d), (second, other) = values
    if (
        any(polynomial(n).degree() > 0 or n <= 0 for n in (first, second))
        or any(polynomial(v).degree() != 1 for v in (d, other))
        or polynomial(d).nth(1) != -polynomial(other).nth(1)
    ):
        raise UnsupportedCondition("the affine denominators must have opposite slopes")
    denominator = sp.Mul(d, other, evaluate=False)
    numerator = sp.expand(first * other + second * d - a.right.value * d * other)
    if polynomial(numerator).degree() != 2:
        raise UnsupportedCondition("the common numerator must be quadratic")
    return [], [
        Step(fraction(numerator, denominator), a.original),
        Step(fraction(real_factor(numerator, a.zeros), denominator), a.original),
    ]


def vieta_quadratic(a):
    p = polynomial(a.left.value)
    if a.right.value != 0 or a.poles or p.degree() != 2 or p.LC() != 1:
        raise UnsupportedCondition(
            "the Vieta parent requires a monic quadratic inequality"
        )
    return [], [Step(latex(real_factor(p.as_expr(), a.zeros)), a.original)]


def cancelled_quadratic_sum(a):
    if a.right.kind != "divide" or len(a.holes) != 1:
        raise UnsupportedCondition(
            "the parent requires one cancelled quadratic fraction"
        )
    numerator, denominator = (node.value for node in a.right.children)
    if any(polynomial(v).degree() != 2 for v in (numerator, denominator)):
        raise UnsupportedCondition(
            "the original fraction must have quadratic polynomials"
        )
    constant = sp.Integer(0)
    fractions = []
    for sign, node in terms(a.left):
        if not node.value.free_symbols:
            constant += sign * node.value
        elif node.kind == "divide":
            n, d = (child.value for child in node.children)
            fractions.append((sign * n, d))
        else:
            raise UnsupportedCondition(
                "the right side must be a scalar and an affine fraction"
            )
    if len(fractions) != 1:
        raise UnsupportedCondition(
            "one affine fraction is required on the source right side"
        )
    n, d = fractions[0]
    reduced_n, reduced_d = sp.fraction(sp.cancel(-numerator / denominator))
    if [polynomial(v).degree() for v in (d, reduced_n, reduced_d)] != [1, 1, 1]:
        raise UnsupportedCondition(
            "cancellation must leave an affine-over-affine fraction"
        )
    first = sp.expand(constant * d + n)
    common = sp.lcm(d, reduced_d)
    combined = sp.expand(
        first * sp.cancel(common / d) + reduced_n * sp.cancel(common / reduced_d)
    )
    return [], [
        Step(fraction(first, d) + "+" + fraction(-numerator, denominator), a.original),
        Step(
            fraction(first, d)
            + "+"
            + fraction(sp.factor(-numerator), sp.factor(denominator)),
            a.original,
        ),
        Step(fraction(first, d) + "+" + fraction(reduced_n, reduced_d), a.original),
        Step(fraction(combined, sp.factor(common)), a.original),
    ]


METHODS = {
    "opposite_fractions": opposite_fractions,
    "vieta_quadratic": vieta_quadratic,
    "cancelled_quadratic_sum": cancelled_quadratic_sum,
}
