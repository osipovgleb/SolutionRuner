"""Exact quadratic-root domains and every denominator from the original syntax."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_parser import polynomial
from .rational_inequality_roots import ordered
from .rational_substitution_preimages import comparison, excluded_points


@dataclass(frozen=True)
class RootDomain:
    roots: object
    values: object
    excluded: tuple
    rational_denominators: tuple


def domain(radicands, denominators):
    if any(polynomial(p).degree() > 2 for p in radicands.values()):
        raise UnsupportedCondition(
            "this original-domain method supports quadratic roots only"
        )
    root_domain = sp.Intersection(
        *(comparison(p, ">=").solution for p in radicands.values())
    )
    rational, excluded = [], set()
    for denominator in denominators:
        active = denominator.free_symbols & radicands.keys()
        if not active:
            rational.append(denominator)
            excluded.update(excluded_points((denominator,)))
            continue
        if len(active) != 1:
            raise UnsupportedCondition(
                "one root at a time is required in a radical denominator"
            )
        symbol = next(iter(active))
        p = sp.Poly(denominator, symbol) if denominator.is_polynomial(symbol) else None
        if (
            p is None
            or p.degree() != 1
            or any(c.is_Rational is not True for c in p.all_coeffs())
        ):
            raise UnsupportedCondition(
                "a radical denominator must be affine in one root with rational coefficients"
            )
        level = -p.nth(0) / p.nth(1)
        if level >= 0:
            zeros = comparison(radicands[symbol] - level**2, "=").solution
            if not isinstance(zeros, sp.FiniteSet) and zeros != sp.EmptySet:
                raise UnsupportedCondition(
                    "a radical denominator needs finitely many excluded points"
                )
            excluded.update(zeros)
    return RootDomain(
        root_domain,
        root_domain - sp.FiniteSet(*excluded),
        ordered(excluded),
        tuple(rational),
    )
