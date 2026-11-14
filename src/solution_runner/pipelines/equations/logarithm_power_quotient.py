"""Use the positive left quotient to imply the right logarithm's domain."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_product_inequality import ProductComparison, read_input
from .rational_inequality import analyze as rational
from .rational_inequality_algebraic_methods import original_orientation
from .rational_inequality_parser import RationalParser, polynomial
from .rational_inequality_roots import ordered, real_roots
from .rational_substitution_preimages import comparison


def analyze(formula):
    operator, base, arguments, texts, constant = read_input(formula, "power_quotient")
    if base <= 1 or operator not in ("<", "<="):
        raise UnsupportedCondition(
            "an increasing-base comparison implying right argument positivity is required"
        )
    domains = tuple(
        original_orientation(rational(text + r"\gt 0")) for text in texts[:2]
    )
    readers = [RationalParser(text) for text in texts]
    for reader in readers:
        reader.parse()
    holes = ordered(
        {
            root
            for reader in readers
            for denominator in reader.denominators
            for root in real_roots(sp.fraction(sp.cancel(denominator))[0])
        }
    )
    domain = sp.Intersection(*(d.solution for d in domains)) - sp.FiniteSet(*holes)
    A, B, C = arguments
    left = sp.cancel(A**2 / B)
    if domain.is_subset(comparison(left, ">").solution) is not True:
        raise UnsupportedCondition("the original left quotient must be positive")
    numerator, denominator = sp.fraction(sp.cancel(C - left))
    if polynomial(numerator).degree() != 3 or polynomial(denominator).degree() > 2:
        raise UnsupportedCondition(
            "a cubic numerator and bounded denominator are required"
        )
    if domain.is_subset(comparison(denominator, ">").solution) is not True:
        raise UnsupportedCondition(
            "the complete comparison denominator must be positive on the original domain"
        )
    reverse = ">" if operator == "<" else ">="
    stage = comparison(numerator, reverse)
    full_stage = comparison(C - left, reverse)
    solution = stage.solution.intersect(domain)
    if full_stage.solution.intersect(domain) != solution:
        raise UnsupportedCondition(
            "the positive denominator reduction changed the solution"
        )
    return ProductComparison(
        formula,
        operator,
        base,
        arguments,
        domains,
        (0, 1),
        domain,
        domain,
        stage,
        solution,
        full_stage,
        texts,
        holes,
        constant,
    )
