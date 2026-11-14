"""Exact sign rationalization with every original logarithm-domain exclusion."""

from dataclasses import dataclass
from functools import cmp_to_key

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rational_substitution import source_order
from .logarithm_rationalization_input import ratio_input, square_input
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_inequality_roots import compare, real_roots
from .rational_substitution_preimages import comparison


def parts(solution):
    if solution == sp.EmptySet:
        return ()
    result = []
    for part in solution.args if isinstance(solution, sp.Union) else (solution,):
        if isinstance(part, sp.FiniteSet):
            result.extend(sp.FiniteSet(point) for point in part)
        elif isinstance(part, sp.Interval) or part == sp.S.Reals:
            result.append(part)
        else:
            raise UnsupportedCondition(
                "only exact real intervals and isolated points are supported"
            )
    return tuple(sorted(result, key=cmp_to_key(source_order)))


def scalar_text(value):
    return sp.latex(sp.together(value))


def answer(solution):
    return (
        r"\cup ".join(set_latex(part, endpoint=scalar_text) for part in parts(solution))
        or r"\varnothing"
    )


def square_image(solution, shift):
    result = []
    for part in parts(solution):
        if part == sp.S.Reals or compare(part.inf, 0) < 0:
            raise UnsupportedCondition(
                "the principal-root inverse must stay nonnegative"
            )
        if isinstance(part, sp.FiniteSet):
            result.append(sp.FiniteSet(*(sp.expand(p**2 - shift) for p in part)))
        else:
            lower = sp.expand(part.start**2 - shift)
            upper = sp.oo if part.end == sp.oo else sp.expand(part.end**2 - shift)
            result.append(
                sp.Interval(
                    lower, upper, left_open=part.left_open, right_open=part.right_open
                )
            )
    return sp.Union(*result)


@dataclass(frozen=True)
class RatioRationalization:
    coordinate: object
    A: sp.Expr
    B: sp.Expr
    power: int
    reference: sp.Expr
    style: object
    right_text: str
    operator: str
    domains: tuple
    holes: tuple
    domain: object
    full_stage: object
    removed: tuple
    stage: object
    working_solution: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def ratio(formula):
    coords, A, B, power, reference, style, right, operator = ratio_input(formula)
    domains = (comparison(A, ">").solution, comparison(B, ">").solution)
    holes = real_roots(B - 1)
    domain = sp.Intersection(*domains) - sp.FiniteSet(*holes)
    if coords.shift is not None:
        domain = domain.intersect(sp.Interval(0, sp.oo))
    full_stage = comparison((A - B) * (B - 1), operator)
    removed = []
    for factor, degree in sp.factor_list(full_stage.original, X)[1]:
        if (
            degree % 2 == 0
            and domain.is_subset(comparison(factor**degree, ">").solution) is True
        ):
            removed.append(factor**degree)
    stage = comparison(sp.cancel(full_stage.original / sp.prod(removed)), operator)
    working = stage.solution.intersect(domain)
    if full_stage.solution.intersect(domain) != working:
        raise UnsupportedCondition(
            "removing a positive square must preserve the full original domain"
        )
    solution = working if coords.shift is None else square_image(working, coords.shift)
    return RatioRationalization(
        coords,
        A,
        B,
        power,
        reference,
        style,
        right,
        operator,
        domains,
        holes,
        domain,
        full_stage,
        tuple(removed),
        stage,
        working,
        solution,
    )


@dataclass(frozen=True)
class SquareDenominator:
    base: sp.Expr
    A: sp.Expr
    B: sp.Expr
    level: sp.Expr
    threshold: sp.Expr
    operator: str
    domain: object
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def square_denominator(formula):
    base, A, B, level, operator = square_input(formula)
    threshold = base**level
    domain = sp.Intersection(
        comparison(A, ">").solution,
        comparison(B, ">").solution,
        comparison(X**2, ">").solution,
    )
    stage = comparison((A - B) / (X**2 - threshold) ** 2, operator)
    return SquareDenominator(
        base,
        A,
        B,
        level,
        threshold,
        operator,
        domain,
        stage,
        stage.solution.intersect(domain),
    )
