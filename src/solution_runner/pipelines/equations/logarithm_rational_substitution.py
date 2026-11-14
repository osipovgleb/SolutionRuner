"""Read monomial logarithms and reuse the exact rational interval calculation."""

import re
from dataclasses import dataclass
from functools import cmp_to_key

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm
from .logarithm_arithmetic import log_ratio
from .logarithm_factor_arguments import read_polynomial
from .power_arithmetic import clean
from .rational_inequality import analyze as rational
from .rational_inequality import set_latex
from .rational_inequality_parser import X, polynomial
from .rational_inequality_roots import compare


@dataclass(frozen=True)
class MonomialLog:
    original: str
    coefficient: sp.Expr
    degree: int
    shift: sp.Expr
    power: int

    @property
    def linear(self):
        return self.shift + self.degree * X


def argument(text):
    value, exclusions = read_polynomial(text)
    p = sp.Poly(value, X)
    if len(p.terms()) != 1 or exclusions - {sp.S.Zero}:
        raise UnsupportedCondition("one original polynomial monomial is required")
    (degree,), coefficient = p.terms()[0]
    if coefficient <= 0 or not 1 <= degree <= 20:
        raise UnsupportedCondition(
            "a positive coefficient and positive bounded power are required"
        )
    return value


def read_input(formula):
    text = clean(formula)
    pieces, outside, terms, bases = [], [], [], []
    while r"\log_" in text:
        if len(terms) >= 12:
            raise UnsupportedCondition("too many complete logarithm occurrences")
        start = text.index(r"\log_")
        outside.append(text[:start])
        pieces.append(text[:start])
        atom, power, end = logarithm(
            text,
            start,
            X,
            extended=True,
            argument_reader=argument,
            argument_powers=True,
        )
        base = atom.base
        if (
            atom.root
            or atom.denominator
            or base.is_Rational is not True
            or base <= 1
            or max(base.p, base.q) > 1000
        ):
            raise UnsupportedCondition(
                "one bounded increasing rational logarithm base is required"
            )
        (degree,), coefficient = sp.Poly(atom.argument, X).terms()[0]
        shift = log_ratio(base, coefficient)
        if shift.is_Rational is not True or abs(shift) > 20:
            raise UnsupportedCondition(
                "the monomial coefficient must be a bounded exact base power"
            )
        term = MonomialLog(text[start:end], coefficient, degree, shift, power)
        terms.append(term)
        bases.append(base)
        replacement = "x" if term.linear == X else "(" + sp.latex(term.linear) + ")"
        pieces.append(replacement + ("^2" if power == 2 else ""))
        text = text[end:]
    pieces.append(text)
    outside.append(text)
    if not terms or len(set(bases)) != 1 or not any(t.degree % 2 for t in terms):
        raise UnsupportedCondition(
            "same-base monomial logarithms must force x to be positive"
        )
    if re.search("x", re.sub(r"\\[a-zA-Z]+", "", "".join(outside))):
        raise UnsupportedCondition(
            "the original variable is allowed only inside complete logarithms"
        )
    return bases[0], tuple(terms), "".join(pieces)


def inverse(base, level):
    if level == -sp.oo:
        return sp.S.Zero
    if level == sp.oo:
        return sp.oo
    if (
        level.is_real is not True
        or level.is_algebraic is not True
        or sp.count_ops(level) > 16
    ):
        raise UnsupportedCondition(
            "a bounded real algebraic logarithm level is required"
        )
    if compare(abs(level), 30) > 0 or sp.degree(sp.minpoly(level)) > 2:
        raise UnsupportedCondition(
            "the logarithm inverse level exceeds the reviewed quadratic range"
        )
    return base**level


def source_order(left, right):
    if left.inf == right.inf:
        return 0
    if left.inf == -sp.oo:
        return -1
    if right.inf == -sp.oo:
        return 1
    return compare(left.inf, right.inf)


@dataclass(frozen=True)
class RationalLogSubstitution:
    base: sp.Expr
    terms: tuple
    transformed: str
    stage: object
    images: tuple
    endpoints: tuple
    domain: object
    solution: object

    def endpoint(self, value):
        for level, actual in self.endpoints:
            if value == actual and level.is_Rational is not True:
                return sp.latex(sp.Pow(self.base, level, evaluate=False))
        return sp.latex(value)

    @property
    def answer(self):
        return (
            r"\cup ".join(
                set_latex(image, endpoint=self.endpoint) for _, image in self.images
            )
            or r"\varnothing"
        )


def analyze(formula):
    base, terms, transformed = read_input(formula)
    stage = rational(transformed)
    n, d = sp.fraction(stage.original)
    if (
        stage.original == 0
        or max(polynomial(n).degree(), polynomial(d).degree()) > 2
        or len(stage.poles) > 4
    ):
        raise UnsupportedCondition(
            "a nonzero quadratic rational comparison with bounded exclusions is required"
        )
    endpoints = tuple((level, inverse(base, level)) for level in stage.points)
    sources = []
    for part in (
        stage.solution.args
        if isinstance(stage.solution, sp.Union)
        else (stage.solution,)
    ):
        if part == sp.EmptySet:
            continue
        if isinstance(part, sp.FiniteSet):
            sources.extend(sp.FiniteSet(point) for point in part)
        else:
            sources.append(part)
    sources.sort(key=cmp_to_key(source_order))
    images = []
    for part in sources:
        if part == sp.EmptySet:
            continue
        if isinstance(part, sp.FiniteSet):
            image = sp.FiniteSet(*(inverse(base, level) for level in part))
        elif part == sp.S.Reals:
            image = sp.Interval.open(0, sp.oo)
        elif isinstance(part, sp.Interval):
            image = sp.Interval(
                inverse(base, part.start),
                inverse(base, part.end),
                left_open=part.left_open,
                right_open=part.right_open,
            )
        else:
            raise UnsupportedCondition(
                "the substitution needs exact intervals and isolated points"
            )
        images.append((part, image))
    domain = sp.Interval.open(0, sp.oo) - sp.FiniteSet(
        *(inverse(base, level) for level in stage.poles)
    )
    solution = sp.Union(*(image for _, image in images))
    if solution.is_subset(domain) is not True:
        raise UnsupportedCondition(
            "the inverse image must retain every original logarithm denominator"
        )
    return RationalLogSubstitution(
        base, terms, transformed, stage, tuple(images), endpoints, domain, solution
    )
