"""Derive affine substitutions and certify their domains and inverse images."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality import Analysis, analyze
from .rational_inequality_methods import divisions, fraction, latex
from .rational_inequality_parser import X, polynomial
from .rational_inequality_roots import compare, ordered

RELATION = {"<=": r"\le", ">=": r"\ge", "<": "<", ">": ">"}


def inverse_set(solution, scale, offset):
    def inverse(value):
        return sp.simplify((value - offset) / scale)

    if isinstance(solution, sp.Union):
        return sp.Union(*(inverse_set(part, scale, offset) for part in solution.args))
    if isinstance(solution, sp.Interval):
        return sp.Interval(
            inverse(solution.start),
            inverse(solution.end),
            left_open=solution.left_open,
            right_open=solution.right_open,
        )
    if isinstance(solution, sp.FiniteSet):
        return sp.FiniteSet(*(inverse(value) for value in solution))
    if solution in (sp.S.Reals, sp.EmptySet):
        return solution
    raise UnsupportedCondition("the substitution needs an exact interval solution")


@dataclass(frozen=True)
class Substitution:
    original: Analysis
    stage: Analysis
    scale: sp.Expr
    offset: sp.Expr
    variable: str
    fractions: tuple = ()
    rows: tuple = ()


def certify(original, stage, scale, offset, variable, *, fractions=(), rows=()):
    if compare(scale, 0) <= 0 or scale.free_symbols or offset.free_symbols:
        raise UnsupportedCondition("a positive constant substitution scale is required")
    substitution = scale * X + offset
    if (
        sp.simplify(stage.original.subs(X, substitution) - original.original) != 0
        or stage.operator != original.operator
        or ordered((p - offset) / scale for p in stage.poles) != original.poles
        or inverse_set(stage.solution, scale, offset) != original.solution
    ):
        raise UnsupportedCondition(
            "the substitution must preserve the expression, domain and answer"
        )
    return Substitution(
        original, stage, scale, offset, variable, tuple(fractions), tuple(rows)
    )


def affine_radical(original):
    values = divisions(original.left)
    if len(values) != 2 or original.right.value.free_symbols:
        raise UnsupportedCondition(
            "two affine fractions and a constant bound are required"
        )
    (first, denominator), (second, other) = values
    if [polynomial(v).degree() for v in (first, denominator, second, other)] != [
        0,
        1,
        1,
        1,
    ]:
        raise UnsupportedCondition(
            "a scalar fraction followed by an affine fraction is required"
        )
    slope = polynomial(denominator).nth(1)
    scale = sp.Abs(slope)
    oriented = sp.expand(compare(slope, 0) * polynomial(denominator).nth(0))
    offset = sp.simplify(oriented - oriented.as_coeff_Add()[0])
    if scale.is_Rational is True:
        raise UnsupportedCondition(
            "the reviewed substitution requires an irrational affine scale"
        )

    def transform(value):
        return sp.simplify(sp.expand(value.subs(X, (X - offset) / scale)))

    fractions = tuple((transform(n), transform(d)) for n, d in values)
    if any(
        c.is_Rational is not True
        for pair in fractions
        for v in pair
        for c in polynomial(v).all_coeffs()
    ):
        raise UnsupportedCondition(
            "the substitution must leave rational polynomial coefficients"
        )
    formula = (
        "+".join(fraction(n, d) for n, d in fractions)
        + RELATION[original.operator]
        + latex(original.right.value)
    )
    stage = analyze(formula)
    if (
        len(stage.poles) != 2
        or stage.holes
        or polynomial(sp.fraction(stage.original)[0]).degree() != 2
    ):
        raise UnsupportedCondition(
            "this source method requires two poles and a quadratic numerator"
        )
    return certify(original, stage, scale, offset, "z", fractions=fractions)


def reciprocal_square(original):
    node = original.left
    if (
        node.kind != "power"
        or node.children[1].value != 2
        or original.operator != "<="
        or original.right.value.free_symbols
        or compare(original.right.value, 4) < 0
    ):
        raise UnsupportedCondition(
            "the parent requires a bounded square of a reciprocal sum"
        )
    values = divisions(node.children[0])
    candidates = [
        sp.cancel(n / d)
        for n, d in values
        if polynomial(n).degree() == 1 and polynomial(d).degree() == 0
    ]
    if len(values) != 2 or len(candidates) != 1:
        raise UnsupportedCondition("one affine term and its reciprocal are required")
    substitution = candidates[0]
    if sp.cancel(node.children[0].value - substitution - 1 / substitution) != 0:
        raise UnsupportedCondition("both source terms must be reciprocal")
    p = polynomial(substitution)
    scale, offset = p.nth(1), p.nth(0)
    bound = sp.sqrt(original.right.value)
    if bound.is_Rational is not True:
        raise UnsupportedCondition(
            "the reviewed reciprocal bound must have a rational square root"
        )
    stage = analyze(r"(\frac{1}{x}+x)^2\le" + latex(original.right.value))
    upper = analyze(fraction(X**2 - bound * X + 1, X) + r"\le0")
    lower = analyze(fraction(X**2 + bound * X + 1, X) + r"\ge0")
    if sp.Intersection(upper.solution, lower.solution) != stage.solution:
        raise UnsupportedCondition(
            "the two interval rows must give the square inequality exactly"
        )
    return certify(original, stage, scale, offset, "t", rows=(upper, lower))


METHODS = {"affine_radical": affine_radical, "reciprocal_square": reciprocal_square}


def model(original, method):
    if method not in METHODS:
        raise UnsupportedCondition(
            "an explicit reviewed substitution method is required"
        )
    return METHODS[method](original)
