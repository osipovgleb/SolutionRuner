"""Reciprocal substitution and equal squares retain every original pole."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import T, X, select_roots
from .exam_rational_input import Y, shifted_laurent, square_fraction, substitution_scale
from .exam_scalar import compare
from .power_arithmetic import clean


@dataclass(frozen=True)
class Selection:
    roots: tuple
    selected: tuple
    interval: str
    bounds: tuple


@dataclass(frozen=True)
class Branch:
    value: sp.Expr
    polynomial: sp.Expr
    candidates: tuple
    roots: tuple


@dataclass(frozen=True)
class Analysis:
    selection: Selection
    pole: sp.Expr
    branches: tuple
    substitution: sp.Expr | None
    quadratic: sp.Expr | None
    original: sp.Expr
    numerators: tuple = ()
    denominator: sp.Expr | None = None


def branch(value, p, pole, original):
    if p == 0:
        raise UnsupportedCondition(
            "an identity branch would require an infinite solution set"
        )
    p = primitive(p, (X,))
    candidates = tuple(real_roots(p, X)) if sp.Poly(p, X).degree() > 0 else ()
    accepted = []
    for root in candidates:
        if compare(root, pole) == 0:
            continue
        if sp.simplify(original.subs(X, root)) != 0:
            raise UnsupportedCondition(
                "each retained root must satisfy the original rational equation"
            )
        accepted.append(root)
    return Branch(value, p, candidates, tuple(accepted))


def reciprocal(formula, interval, bounds, parent_html):
    pole, translated, expression = shifted_laurent(formula)
    u = substitution_scale(translated, parent_html)
    linear = expression.coeff(Y, 1)
    if linear == 0:
        raise UnsupportedCondition(
            "the reviewed reciprocal substitution needs a nonzero linear term"
        )
    v = sp.cancel(expression.coeff(Y, -1) * u / linear)
    if v.is_Rational is not True or v >= 0:
        raise UnsupportedCondition(
            "the reciprocal part must have one exact negative coefficient"
        )
    substitution = u * Y + v / Y
    A = expression.coeff(Y, 2) / u**2
    B = linear / u
    C = expression.coeff(Y, 0) - 2 * A * u * v
    if (
        A == 0
        or sp.cancel(expression - (A * substitution**2 + B * substitution + C)) != 0
    ):
        raise UnsupportedCondition(
            "the entire Laurent equation must equal one reciprocal quadratic"
        )
    quadratic = primitive(A * T * T + B * T + C, (T,))
    levels = real_roots(quadratic, T)
    if any(t.is_Rational is not True for t in levels):
        raise UnsupportedCondition(
            "the reviewed reciprocal back-substitution requires rational levels"
        )
    original = expression.subs(Y, X - pole)
    branches = tuple(
        branch(t, sp.expand(u * (X - pole) ** 2 - t * (X - pole) + v), pole, original)
        for t in levels
    )
    roots, selected = select_roots([r for b in branches for r in b.roots], bounds)
    return Analysis(
        Selection(roots, selected, interval, bounds),
        pole,
        branches,
        substitution,
        quadratic,
        original,
    )


def equal_squares(formula, interval, bounds, left, right):
    P, D = left
    Q, other = right
    if sp.simplify(D - other) != 0:
        raise UnsupportedCondition("both original denominators must be exactly equal")
    d = sp.Poly(D, X)
    pole = sp.simplify(-d.nth(0) / d.nth(1))
    original = (P * P - Q * Q) / D
    branches = tuple(
        branch(sign, sp.expand(P - sign * Q), pole, original)
        for sign in (sp.Integer(1), sp.Integer(-1))
    )
    roots, selected = select_roots([r for b in branches for r in b.roots], bounds)
    return Analysis(
        Selection(roots, selected, interval, bounds),
        pole,
        branches,
        None,
        None,
        original,
        (P, Q),
        D,
    )


def analyze(formula, interval, bounds, parent_html):
    text = clean(formula)
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete rational equation is required")
    left, right = (square_fraction(part) for part in text.split("="))
    if left is not None and right is not None:
        from bs4 import BeautifulSoup

        text = (
            BeautifulSoup(parent_html, "html.parser")
            .get_text(" ", strip=True)
            .replace("\xad", "")
            .lower()
        )
        if "квадраты" not in text or "противоположны" not in text:
            raise UnsupportedCondition(
                "the parent must use equality of squares with the original denominator"
            )
        return equal_squares(formula, interval, bounds, left, right)
    return reciprocal(formula, interval, bounds, parent_html)


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_input import read, repair
    from .exam_rational_proof import render

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    return repair(parts, *render(a))
