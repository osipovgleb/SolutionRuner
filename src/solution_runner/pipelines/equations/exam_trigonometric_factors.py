"""Retain variable coefficients and separate affine sine/cosine factors."""

from dataclasses import replace

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
    if set().union(*variables) != {S, C} or any(
        not v or not v <= {S, C} for v in variables
    ):
        return None
    if any(
        sp.Poly(f, S, C).total_degree() != 1
        or (len(v) == 2 and f.subs({S: 0, C: 0}) != 0)
        for (f, _), v in zip(factors, variables)
    ):
        return None
    result = []
    from .exam_trigonometric_ratios import linear_branch

    for factor, _ in sorted(
        factors,
        key=lambda item: (len(item[0].free_symbols) > 1, not item[0].has(preferred)),
    ):
        if factor.free_symbols == {S, C}:
            result.append(linear_branch(factor))
        else:
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


def zero_square(raw):
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() != 3:
        return None
    for variable in (S, C):
        reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, variable))
        _, factors = sp.factor_list(reduced, S, C, extension=True)
        if len(factors) != 2:
            continue
        zero = next((f for f, power in factors if f in (S, C) and power == 2), None)
        if zero is None:
            continue
        other = next(f for f, _ in factors if f != zero)
        if (
            other.free_symbols == ({S, C} - {zero})
            and sp.Poly(other, *other.free_symbols).degree() == 1
        ):
            return reduced
    return None


def preserve_zero_square(compiled, parent_html):
    from .exam_trigonometric_style import zero_square_method

    if not zero_square_method(parent_html):
        return compiled
    reduced = zero_square(compiled.raw)
    return (
        replace(compiled, raw=reduced, factored_source=compiled.raw)
        if reduced is not None
        else compiled
    )


def method_branches(
    compiled, preferred, allow_inverse, domain, parent_html, *, translation=sp.S.Zero
):
    from ..word_problems.common import UnsupportedCondition
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_compile import T, U
    from .exam_trigonometric_domain import restrict, without_poles
    from .exam_trigonometric_factor_style import (
        local_cotangent,
        mark_grouping,
        retain_order,
    )
    from .exam_trigonometric_homogeneous import convert
    from .exam_trigonometric_square_factor import mark as mark_squares
    from .exam_trigonometric_square_factor import prepare as square_product
    from .exam_trigonometric_style import cotangent_method

    compiled = square_product(compiled, parent_html) if domain is None else compiled
    if compiled.square_difference is not None:
        from .exam_trigonometric_square_difference import parameter

        data = replace(compiled.square_difference, parameter=parameter(parent_html))
        compiled = replace(compiled, square_difference=data)
    from .exam_trigonometric_symmetric import branches as sum_branches
    from .exam_trigonometric_symmetric import prepare

    symmetric = prepare(compiled, parent_html, translation) if domain is None else None
    if symmetric is not None:
        result = sum_branches(symmetric.symmetric, parent_html)
        return symmetric, symmetric.raw, result, preferred
    if compiled.angle_product is not None:
        from .exam_trigonometric_angle_product import branches as angle_branches

        return compiled, compiled.raw, angle_branches(compiled.angle_product), preferred
    if not compiled.raw.has(T, U) and cotangent_method(parent_html):
        preferred = C if local_cotangent(parent_html) else U
    compiled = convert(compiled, preferred)
    compiled = preserve_zero_square(compiled, parent_html)
    reduced, branches = solve_branches(
        compiled.raw,
        preferred,
        allow_inverse,
        factored=compiled.factored_source is not None
        or compiled.square_product is not None,
    )
    compiled, branches = retain_order(compiled, reduced, branches, parent_html, domain)
    if domain is not None:
        branches = restrict(branches, domain, compiled.strict_domain)
    if any(b.angle_shift for b in branches):
        from .exam_trigonometric_linear_phase import notation

        branches = notation(branches, parent_html)
    branches = without_poles(branches, compiled.poles)
    if compiled.cleared_denominator is not None and preferred == T:
        branches = tuple(sorted(branches, key=lambda b: b.variable != T))
    if any(b.angle_shift for b in branches) and domain is not None:
        raise UnsupportedCondition(
            "shifted linear factors require a denominator-free equation"
        )
    if domain is None and not compiled.poles:
        branches = mark_grouping(branches, parent_html)
    branches = mark_squares(branches, parent_html, compiled.square_product)
    return compiled, reduced, branches, preferred
