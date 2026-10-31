"""Homogenize on the unit circle and divide only after excluding zero cosine."""

from dataclasses import dataclass, replace

import sympy as sp

from ..word_problems.math_common import primitive
from .exam_trigonometric_compile import C, S, T, U


@dataclass(frozen=True)
class Reduction:
    source: sp.Expr
    source_scale: sp.Rational
    polynomial: sp.Expr
    degree: int
    variable: sp.Symbol = T


def lift(raw, variable=T):
    if not raw.is_polynomial(S, C):
        return None
    source = raw
    if sp.Poly(raw, S, C).total_degree() > 3:
        raw = sp.expand(sp.rem(raw, S * S + C * C - 1, S))
    poly = sp.Poly(raw, S, C)
    degree = poly.total_degree()
    if degree not in (1, 2, 3) or any(
        (degree - sum(powers)) % 2 for powers, _ in poly.terms()
    ):
        return None
    homogeneous = sp.expand(
        sum(
            coefficient
            * S ** powers[0]
            * C ** powers[1]
            * (S * S + C * C) ** ((degree - sum(powers)) // 2)
            for powers, coefficient in poly.terms()
        )
    )
    if sp.rem(homogeneous - source, S * S + C * C - 1, S) != 0:
        return None
    if homogeneous.coeff(C if variable == U else S, degree) == 0:
        return None
    return primitive(homogeneous, (S, C)), degree


def convert(equation, preferred):
    raw = equation.raw
    if raw.has(T, U) or equation.reciprocal is not None:
        return equation
    if equation.poles:
        from .exam_trigonometric_grouping import branches

        if branches(raw) is not None:
            return equation
    linear = (
        raw.free_symbols == {S, C}
        and sp.Poly(raw, S, C).total_degree() == 1
        and raw.subs({S: 0, C: 0}) == 0
    )
    if preferred not in (T, U) and not linear:
        return equation
    variable = U if preferred == U else T
    lifted = lift(raw, variable)
    if lifted is None:
        return equation
    homogeneous, degree = lifted
    scale = equation.scale
    if degree == 2 and not equation.poles:
        a = homogeneous.coeff(S, 2)
        if homogeneous.coeff(C, 2) == -a:
            homogeneous = sp.expand(homogeneous.coeff(S).coeff(C) * S / 2 - a * C)
            scale *= 2
            degree = 1
    reduction = Reduction(raw, equation.scale, homogeneous, degree, variable)
    return replace(
        equation,
        raw=sp.expand(
            homogeneous.subs({C: U, S: 1} if variable == U else {S: T, C: 1})
        ),
        scale=scale,
        homogeneous=reduction,
    )
