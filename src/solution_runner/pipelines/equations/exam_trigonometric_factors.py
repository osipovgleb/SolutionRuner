"""Retain variable coefficients and separate affine sine/cosine factors."""

import sympy as sp

from .exam_trigonometric_compile import C, S


def source_factors(raw):
    coefficient, factors = sp.factor_list(raw, S, C)
    values = [p for p, _ in factors]
    if coefficient.has(S, C):
        values.append(coefficient)
    return values


def separated(raw, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches

    coefficient, factors = sp.factor_list(raw, S, C, extension=True)
    if coefficient.has(S, C) or len(factors) != 2:
        return None
    variables = [f.free_symbols for f, _ in factors]
    if set().union(*variables) != {S, C} or any(len(v) != 1 for v in variables):
        return None
    if any(sp.Poly(f, *v).degree() != 1 for (f, _), v in zip(factors, variables)):
        return None
    result = []
    for factor, _ in sorted(factors, key=lambda item: not item[0].has(preferred)):
        variable = next(iter(factor.free_symbols))
        result.extend(solve_branches(factor, variable, allow_inverse)[1])
    return raw, tuple(result)


def project(raw, preferred):
    other = S if preferred == C else C
    reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, other))
    if not reduced.has(other):
        expressions = [reduced]
    else:
        alternative = sp.expand(sp.rem(raw, S * S + C * C - 1, preferred))
        if not alternative.has(preferred):
            reduced = alternative
            expressions = [reduced]
        else:
            expressions = source_factors(raw)
    return reduced, expressions
