"""Split a root quotient by the sign of its original logarithm denominator."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_radical_input import read
from .logarithm_rational_substitution import solution_images
from .radical_inequality_domains import domain
from .radical_inequality_parser import RadicalParser
from .rational_inequality import set_latex
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class LogarithmRoot:
    base: sp.Expr
    scale: sp.Expr
    coefficient: sp.Expr
    bound: sp.Expr
    radicand: sp.Expr
    side: sp.Expr
    domain: object
    negative_stage: object
    positive_stage: object
    negative: object
    positive: object
    negative_image: object
    positive_image: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def read_quotient(formula):
    base, text = read(formula)
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", text)
    if len(parts) != 3 or parts[1] not in (r"\lt", "<"):
        raise UnsupportedCondition("one complete strict upper comparison is required")
    radicands, denominators = {}, []
    left, right = (
        RadicalParser(p, denominators, radicands=radicands).parse()
        for p in (parts[0], parts[2])
    )
    if (
        left.kind != "divide"
        or len(radicands) != 1
        or right.value.is_Rational is not True
        or not 0 < right.value <= 40
    ):
        raise UnsupportedCondition(
            "one complete root quotient and a positive rational bound are required"
        )
    numerator, denominator = left.children
    if (
        numerator.kind != "subtract"
        or numerator.children[0].value != 1
        or numerator.children[1].kind != "root"
    ):
        raise UnsupportedCondition("the whole numerator must be one minus one root")
    Q = radicands[numerator.children[1].value]
    p, d = polynomial(Q), polynomial(denominator.value)
    if (
        p.degree() != 2
        or p.nth(0) != 1
        or p.nth(1) != 0
        or p.LC() >= 0
        or d.degree() != 1
        or d.nth(0) != 0
        or d.LC() <= 0
    ):
        raise UnsupportedCondition(
            "an even downward quadratic under the root and a positive multiple of the logarithm in the denominator are required"
        )
    a, c, r = -p.LC(), d.LC(), right.value
    if any(v.is_Rational is not True or v > 40 or v.q > 20 for v in (a, c, r)):
        raise UnsupportedCondition(
            "bounded positive rational root-quotient coefficients are required"
        )
    constraints = domain(radicands, denominators)
    if constraints.excluded != (sp.S.Zero,):
        raise UnsupportedCondition(
            "additional original denominator poles are outside the reviewed parent method"
        )
    return base, a, c, r


def analyze(formula):
    base, a, c, r = read_quotient(formula)
    A = a / c**2
    if r**2 > A:
        raise UnsupportedCondition(
            "the positive-denominator parent branch requires a nonnegative side before squaring"
        )
    Q = 1 - A * X**2
    side = 1 - r * X
    values = comparison(Q, ">=").solution - sp.FiniteSet(0)
    negative_stage = comparison(Q - side**2, "<")
    positive_stage = comparison(Q - side**2, ">")
    negative = sp.Intersection(
        values, sp.Interval.open(-sp.oo, 0), negative_stage.solution
    )
    positive = sp.Intersection(
        values, sp.Interval.open(0, sp.oo), positive_stage.solution
    )
    if not isinstance(negative, sp.Interval) or not isinstance(positive, sp.Interval):
        raise UnsupportedCondition(
            "the two parent branches must give one interval each"
        )

    def image(part):
        coordinate = sp.Interval(
            part.start / c,
            part.end / c,
            left_open=part.left_open,
            right_open=part.right_open,
        )
        return sp.Union(*(v for _, v in solution_images(base, coordinate)))

    neg_image, pos_image = image(negative), image(positive)
    return LogarithmRoot(
        base,
        c,
        A,
        r,
        Q,
        side,
        values,
        negative_stage,
        positive_stage,
        negative,
        positive,
        neg_image,
        pos_image,
        neg_image.union(pos_image),
    )
