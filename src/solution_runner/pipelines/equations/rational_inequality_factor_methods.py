"""Factor common squares without discarding zeros or original denominator restrictions."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_division_methods import difference, step
from .rational_inequality_methods import Step, fraction
from .rational_inequality_parser import X, polynomial


def quartic_cancel(a):
    whole, values = difference(a)
    if (
        whole.free_symbols
        or len(values) != 2
        or len(a.holes) != 1
        or [(polynomial(n).degree(), polynomial(d).degree()) for n, d in values]
        != [(4, 2), (3, 1)]
    ):
        raise UnsupportedCondition(
            "a cancellable quartic fraction and a cubic fraction are required"
        )
    (n, d), (other, e) = values
    square = sp.cancel(n / X**2)
    if (
        not square.is_polynomial(X)
        or polynomial(square).degree() != 2
        or sp.discriminant(polynomial(square)) != 0
        or polynomial(square).LC() <= 0
        or polynomial(sp.gcd(n, d)).degree() != 1
    ):
        raise UnsupportedCondition(
            "the quartic must factor into x squared and an affine square"
        )
    corrected = sp.expand(other + whole * e)
    reduced_n, reduced_d = sp.fraction(sp.cancel(n / d))
    multiplier = sp.cancel(e / reduced_d)
    if multiplier.free_symbols:
        raise UnsupportedCondition(
            "both fractions must have the same affine denominator after cancellation"
        )
    combined = sp.expand(reduced_n * multiplier + corrected)
    if polynomial(combined).degree() not in (2, 3):
        raise UnsupportedCondition("the combined numerator must be quadratic or cubic")
    return [], [
        step(0, [(sp.factor(n), sp.factor(d)), (corrected, e)]),
        step(0, [(reduced_n, reduced_d), (corrected, e)]),
        Step(fraction(combined, e), sp.cancel(combined / e)),
    ]


def square_parameters(a):
    if a.left.kind != "divide" or a.right.kind != "divide" or a.holes:
        raise UnsupportedCondition(
            "two fractions with the same square numerator and no cancelled poles are required"
        )
    n, d = (node.value for node in a.left.children)
    other_n, other_d = (node.value for node in a.right.children)
    p = polynomial(n)
    extra = sp.cancel(other_d / d)
    if (
        sp.expand(n - other_n) != 0
        or p.degree() != 2
        or sp.discriminant(p) != 0
        or p.LC() <= 0
        or polynomial(d).degree() != 1
        or not extra.is_polynomial(X)
        or polynomial(extra).degree() != 1
        or len(a.poles) != 2
    ):
        raise UnsupportedCondition(
            "the expanded numerator must be the same affine square"
        )
    root = sp.simplify(-p.nth(1) / (2 * p.nth(2)))
    if root in a.poles or sp.simplify(extra.subs(X, root) - 1) == 0:
        raise UnsupportedCondition(
            "the reviewed square zero must remain a distinct double zero"
        )
    return sp.factor(n), d, extra, root


def common_square(a):
    n, d, extra, _ = square_parameters(a)
    first = fraction(n, d) + "-" + fraction(n, sp.factor(d * extra))
    extracted = fraction(n, d) + r"\left(1-\frac{1}{" + sp.latex(extra) + r"}\right)"
    combined = sp.Mul(n, extra - 1, evaluate=False)
    return [], [
        Step(first, a.original),
        Step(extracted, a.original),
        Step(fraction(combined, sp.factor(d * extra)), a.original),
    ]


def positive_quadratics(a):
    result = []
    for factor, _ in sp.factor_list(sp.fraction(a.expression)[0])[1]:
        p = polynomial(factor)
        if p.degree() != 2 or sp.discriminant(p) >= 0:
            continue
        coefficient, b, c = p.all_coeffs()
        center = sp.simplify(-b / (2 * coefficient))
        minimum = sp.simplify(c - b**2 / (4 * coefficient))
        if coefficient <= 0 or minimum <= 0:
            raise UnsupportedCondition(
                "the displayed irreducible quadratic must be positive"
            )
        square = (X - center) ** 2
        term = (
            square if coefficient == 1 else sp.Mul(coefficient, square, evaluate=False)
        )
        completed = sp.Add(term, minimum, evaluate=False)
        if sp.expand(completed - factor) != 0:
            raise UnsupportedCondition("the completed-square identity must be exact")
        result.append((factor, completed))
    return result


METHODS = {"quartic_cancel": quartic_cancel, "common_square": common_square}
