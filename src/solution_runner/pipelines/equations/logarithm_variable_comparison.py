"""Keep cancelled logarithm bases and use existing exact polynomial preimages."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm
from .logarithm_factor_arguments import read_polynomial
from .logarithm_rationalization import answer, parts
from .logarithm_rationalization_input import fraction_parts
from .power_arithmetic import balanced, clean
from .rational_inequality import FLIPPED, OPERATORS
from .rational_inequality_parser import X, polynomial
from .rational_inequality_roots import real_roots
from .rational_substitution_preimages import branches, comparison


def strict_polynomial(text):
    value, excluded = read_polynomial(text)
    if excluded:
        raise UnsupportedCondition("hidden original argument poles are not reviewed")
    return value


def read_log(raw):
    raw = re.sub(r"\\log_x(?![a-zA-Z])", r"\\log_{x}", raw)
    text = clean(raw)
    style = r"\lg" if text.startswith(r"\lg") else None
    if style:
        text = r"\log_{10}" + text[3:]
    if not text.startswith(r"\log_"):
        raise UnsupportedCondition("one complete polynomial logarithm is required")
    atom, power, end = logarithm(
        text, 0, X, extended=True, argument_reader=strict_polynomial
    )
    if power != 1 or atom.root or end != len(text):
        raise UnsupportedCondition("external terms or powers cannot be discarded")
    return atom, style


def quotient(text):
    text = clean(text)
    if not text.startswith(r"\frac"):
        raise UnsupportedCondition("one whole logarithm quotient is required")
    n, index = balanced(text, 5)
    d, index = balanced(text, index)
    if index != len(text):
        raise UnsupportedCondition("the whole quotient must be consumed")
    return read_log(n), read_log(d)


@dataclass(frozen=True)
class BaseQuotient:
    G: sp.Expr
    P: sp.Expr
    alpha: sp.Expr
    beta: sp.Expr
    c: sp.Expr
    reference: sp.Expr
    style: object
    operator: str
    base_domain: object
    domain: object
    stage: object
    working_solution: object
    branches: tuple
    preimage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def quadratic_substitution(A, B, C, G):
    gp = polynomial(G)
    bp = polynomial(B)
    if (
        gp.degree() != 1
        or gp.LC() != 1
        or abs(gp.nth(0)) > 20
        or bp.degree() != 2
        or bp.LC() != 1
    ):
        raise UnsupportedCondition(
            "an affine base and a monic quadratic substitution are required"
        )
    c = -bp.nth(0)
    P = sp.expand(B + c)
    alpha = polynomial(A).nth(2)
    beta = sp.expand(A - alpha * P)
    if (
        c.is_Integer is not True
        or not 1 <= c <= 10
        or sp.expand(C - P**2) != 0
        or alpha <= 0
        or beta.is_Rational is not True
        or beta <= 0
        or max(alpha, beta) > 1000
    ):
        raise UnsupportedCondition(
            "the complete arguments must share the reviewed positive quadratic substitution"
        )
    return P, alpha, beta, c


def quotient_comparison(formula):
    n, d, right, operator = fraction_parts(formula)
    first, _ = read_log(n)
    second, _ = read_log(d)
    (third, style), (fourth, other_style) = quotient(right)
    G = first.base
    B = second.argument
    A = first.argument
    C = third.argument
    b = third.base
    if (
        G != second.base
        or B != fourth.argument
        or b != fourth.base
        or style != other_style
    ):
        raise UnsupportedCondition(
            "the two complete quotient bases and denominator arguments must match"
        )
    if b.is_Rational is not True or b <= 1 or max(b.p, b.q) > 1000:
        raise UnsupportedCondition(
            "one bounded increasing numeric reference is required"
        )
    P, alpha, beta, c = quadratic_substitution(A, B, C, G)
    base_domain = comparison(G, ">").solution - sp.FiniteSet(*real_roots(G - 1))
    domain = base_domain.intersect(comparison(P - c, ">").solution) - sp.FiniteSet(
        *real_roots(P - c - 1)
    )
    stage = comparison((X**2 - alpha * X - beta) / (X - c - 1), FLIPPED[operator])
    working = stage.solution.intersect(comparison(X - c, ">").solution)
    inverses = tuple(
        branch
        for part in parts(working)
        for branch in branches(
            part, sp.S.Reals, lambda level, op: comparison(P - level, op)
        )
    )
    preimage = sp.Union(*(branch.solution for branch in inverses))
    solution = preimage.intersect(domain)
    return BaseQuotient(
        G,
        P,
        alpha,
        beta,
        c,
        b,
        style,
        operator,
        base_domain,
        domain,
        stage,
        working,
        inverses,
        preimage,
        solution,
    )


@dataclass(frozen=True)
class CubicComparison:
    A: sp.Expr
    B: sp.Expr
    first_stage: object
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def cubic_comparison(formula):
    pieces = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(pieces) != 3 or pieces[1] not in OPERATORS or OPERATORS[pieces[1]] != "<=":
        raise UnsupportedCondition(
            "one complete increasing cubic logarithm comparison is required"
        )
    first, _ = read_log(pieces[0])
    second, _ = read_log(pieces[2])
    A = first.argument
    B = second.argument
    constant = sp.expand(X**3 - A)
    if (
        first.base != X
        or second.base != X
        or constant.is_Integer is not True
        or not 1 <= constant <= 1000
    ):
        raise UnsupportedCondition(
            "the common base must be x and the first argument x cubed minus a positive integer cube"
        )
    root = sp.real_root(constant, 3)
    difference = polynomial(B - A)
    if root.is_Integer is not True or difference.degree() != 1 or difference.LC() <= 0:
        raise UnsupportedCondition(
            "an exact positive cube threshold and increasing affine argument difference are required"
        )
    first_stage = comparison(A, ">")
    if first_stage.solution.is_subset(sp.Interval.open(1, sp.oo)) is not True:
        raise UnsupportedCondition(
            "the first argument must force the logarithm base above one"
        )
    stage = comparison(A - B, "<=")
    solution = first_stage.solution.intersect(stage.solution)
    return CubicComparison(A, B, first_stage, stage, solution)
