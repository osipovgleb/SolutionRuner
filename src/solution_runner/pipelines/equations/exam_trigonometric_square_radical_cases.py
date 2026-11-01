"""Certify the parent's nonnegative substitution and remaining absolute branches."""

from dataclasses import replace
from functools import cmp_to_key

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation
from .exam_trigonometric_square_radicals import SquareRadicals


def levels(polynomial):
    if not polynomial.is_polynomial(S) or sp.degree(polynomial, S) not in (1, 2):
        raise UnsupportedCondition(
            "the reviewed absolute substitution needs degree one or two"
        )
    return tuple(sorted(roots(polynomial.subs(S, X)), key=cmp_to_key(compare)))


def compile_cases(scale, remainder, coefficients, radicands, linears, method):
    if method == "linear_absolute":
        return compile_linear(scale, remainder, coefficients, radicands, linears)
    if method == "absolute_level":
        if (
            len(linears) != 1
            or linears[0] != S
            or remainder.has(C)
            or remainder.coeff(S) != 0
        ):
            raise UnsupportedCondition(
                "the nonnegative substitution requires |sin| and an even quadratic"
            )
        polynomial = sp.expand(remainder + coefficients[0] * S)
        candidates = (levels(polynomial),)
        accepted = tuple(
            v
            for v in candidates[0]
            if compare(v, sp.S.Zero) >= 0 and compare(v, sp.S.One) <= 0
        )
        cases, signs = (polynomial,), (0,)
        raw = sp.prod(S * S - v * v for v in accepted)
    elif method == "remaining_absolute":
        if len(linears) != 2 or any(v.has(C) for v in (*linears, remainder)):
            raise UnsupportedCondition("two univariate square radicals are required")
        first = linears[0]
        sign = (
            1
            if min(first.subs(S, -1), first.subs(S, 1)) >= 0
            else -1
            if max(first.subs(S, -1), first.subs(S, 1)) <= 0
            else 0
        )
        if not sign:
            raise UnsupportedCondition(
                "the first module must have a certified fixed sign"
            )
        right = sp.expand(
            -(remainder + coefficients[0] * sign * first) / coefficients[1]
        )
        cases = tuple(sp.expand(linears[1] - choice * right) for choice in (1, -1))
        candidates = tuple(levels(p) for p in cases)
        accepted = tuple(
            dict.fromkeys(
                v
                for row in candidates
                for v in row
                if -1 <= v <= 1
                and sp.simplify(
                    remainder.subs(S, v)
                    + sum(c * abs(l.subs(S, v)) for c, l in zip(coefficients, linears))
                )
                == 0
            )
        )
        signs = (sign, 0)
        raw = sp.prod(S - v for v in accepted)
    else:
        raise UnsupportedCondition("unknown square-radical parent method")
    if not accepted:
        raise UnsupportedCondition("no admissible absolute-value level remains")
    data = SquareRadicals(
        radicands,
        linears,
        coefficients,
        remainder,
        signs,
        cases,
        candidates,
        accepted,
        method,
    )
    return Equation(raw, (), scale, square_radicals=data)


def branches(compiled, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict

    result = tuple(
        branch
        for case in compiled.square_radicals.cases
        for branch in solve_branches(case, preferred, allow_inverse)[1]
    )
    return compiled.raw, restrict(result, compiled.domain)


def prepare(a, parent_html):
    if a.square_radicals is None or a.square_radicals.method != "linear_absolute":
        return a
    from .exam_trigonometric import select
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    source = tuple(
        dict.fromkeys(
            (q, p)
            for q, p, _ in affine_families(parent_html)
            if equivalent_series((*a.series, (q, p)), a.series)
        )
    )
    if not source or not equivalent_series(source, a.series):
        raise UnsupportedCondition(
            "the final parent families must match the complete absolute-value solution"
        )
    selected, trace = select(source, a.bounds)
    return replace(
        a,
        series=source,
        selected=selected,
        selections=trace,
        series_aligned=source != a.series,
    )


def compile_linear(scale, remainder, coefficients, radicands, linears):
    method = "linear_absolute"
    if len(linears) != 1 or any(
        sp.Poly(p, S, C).total_degree() != 1 for p in (linears[0], remainder)
    ):
        raise UnsupportedCondition("one affine unit-circle absolute value is required")
    right = sp.expand(-remainder / coefficients[0])
    cases = tuple(sp.expand(linears[0] - sign * right) for sign in (1, -1))
    if any(not p.free_symbols or sp.Poly(p, S, C).total_degree() != 1 for p in cases):
        raise UnsupportedCondition(
            "both absolute branches must remain nonconstant linear equations"
        )
    data = SquareRadicals(
        radicands, linears, coefficients, remainder, (), cases, (), (), method
    )
    return Equation(sp.prod(cases), (), scale, domain=right, square_radicals=data)
