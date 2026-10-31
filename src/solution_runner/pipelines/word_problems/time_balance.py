"""Exact rational time equations, original poles and physical root domains."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import real_roots
from . import math_common
from .common import UnsupportedCondition

X = sp.Symbol("x", real=True)


@dataclass(frozen=True)
class Balance:
    left: sp.Expr
    right: sp.Expr
    domain: sp.Set
    denominators: tuple
    output: sp.Expr = X


def solve(b):
    numerator = sp.together(b.left - b.right).as_numer_denom()[0]
    polynomial = math_common.primitive(numerator, (X,))
    if sp.degree(polynomial, X) not in (1, 2):
        raise UnsupportedCondition("a linear or quadratic time balance is required")
    roots = tuple(sorted(real_roots(polynomial, X), reverse=True))
    valid = [
        r
        for r in roots
        if b.domain.contains(r) is sp.true
        and all(d.subs(X, r) != 0 for d in b.denominators)
    ]
    if len(valid) != 1 or valid[0].is_Rational is not True:
        raise UnsupportedCondition(
            "one exact rational physical root is required without rounding"
        )
    root = valid[0]
    if sp.simplify((b.left - b.right).subs(X, root)) != 0:
        raise UnsupportedCondition("the root must satisfy the original time balance")
    result = sp.cancel(b.output.subs(X, root))
    if result.is_Rational is not True or result <= 0:
        raise UnsupportedCondition(
            "one positive exact rational requested quantity is required"
        )
    return polynomial, roots, root, result
