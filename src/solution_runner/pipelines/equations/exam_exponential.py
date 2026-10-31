"""Positive exponential substitution and exact root selection for exam subparts."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser

X = sp.Symbol("x", real=True)
T = sp.Symbol("t", real=True)


def polynomial(text):
    p = LaurentParser(text)
    v = symbolic(p.parse())
    if (
        p.nonzero
        or v.free_symbols - {X}
        or not v.is_polynomial(X)
        or sp.Poly(v, X).degree() > 2
    ):
        raise UnsupportedCondition(
            "the exponent must be a polynomial in x of degree at most two"
        )
    return v


def terms(formula):
    from .exam_power_terms import read

    powers, constant = read(formula)
    if len(powers) not in (2, 3):
        raise UnsupportedCondition("two or three exponential terms are required")
    return powers, constant


@dataclass(frozen=True)
class Analysis:
    formula: str
    base: sp.Rational
    exponent: sp.Expr
    coefficients: tuple
    t_roots: tuple
    roots: tuple
    selected: tuple
    interval: str
    bounds: tuple
    back: tuple
    divisor: tuple | None = None
    explicit: bool = True


def analyze(formula, interval, bounds, parent_html):

    powers, c = terms(formula)
    from .exam_exponential_parent import style

    shifted, explicit = style(parent_html)
    divisor = None
    if len(powers) == 3:
        from .exam_homogeneous import normalize

        if c != 0:
            raise UnsupportedCondition(
                "a homogeneous equation cannot have an additional constant"
            )
        base, g, (a, b, c), divisor = normalize(powers, shifted)
    else:
        high, low = powers
        if high[1] != low[1] ** 2:
            raise UnsupportedCondition(
                "the first base must be the square of the second"
            )
        base = low[1]
        g = low[2] if shifted else low[2] - low[2].subs(X, 0)
        offsets = (sp.expand(2 * high[2] - 2 * g), sp.expand(low[2] - g))
        if any(
            v.free_symbols or v.is_Rational is not True or abs(v) > 100 for v in offsets
        ):
            raise UnsupportedCondition(
                "both powers must reduce to one positive substitution"
            )
        a, b = high[0] * base ** offsets[0], low[0] * base ** offsets[1]
    if any(v.is_Rational is not True for v in (a, b, c)) or a == 0:
        raise UnsupportedCondition(
            "the transformed quadratic must have exact rational coefficients"
        )
    tr = tuple(real_roots(a * T * T + b * T + c, T))
    roots, back = back_substitute(base, g, tr)
    roots, selected = select_roots(roots, bounds)
    return Analysis(
        formula,
        base,
        g,
        (a, b, c),
        tr,
        roots,
        selected,
        interval,
        bounds,
        tuple(back),
        divisor,
        explicit,
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_exponential_proof import render
    from .exam_input import read, repair

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    return repair(parts, *render(a))


def back_substitute(base, g, tr):
    from .exam_scalar import compare

    roots = []
    back = []
    for t in tr:
        if compare(t, sp.Integer(0)) <= 0:
            continue
        value = sp.cancel(sp.expand_log(sp.log(t) / sp.log(base)))
        p = sp.Poly(g - value, X)
        if p.degree() == 1:
            branch = (sp.cancel(sp.expand_log(-p.nth(0) / p.nth(1))),)
            roots.extend(branch)
        elif p.degree() == 2 and value.is_Rational:
            branch = tuple(real_roots(p.as_expr(), X))
            roots.extend(branch)
        else:
            raise UnsupportedCondition(
                "the back-substitution must be affine or an exact rational quadratic"
            )
        back.append((t, value, branch))
    return roots, back


def select_roots(roots, bounds):
    from functools import cmp_to_key

    from .exam_scalar import compare

    roots = tuple(sorted(set(roots), key=cmp_to_key(compare)))
    lo, hi, lc, uc = bounds
    selected = tuple(
        r
        for r in roots
        if (compare(r, lo) > 0 or (lc and compare(r, lo) == 0))
        and (compare(r, hi) < 0 or (uc and compare(r, hi) == 0))
    )
    return roots, selected
