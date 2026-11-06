"""Exact interval signs with every original pole, including cancelled holes."""

import re
from dataclasses import dataclass
from itertools import pairwise

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_parser import RationalParser, X, polynomial

OPERATORS = {
    r"\le": "<=",
    r"\leq": "<=",
    r"\ge": ">=",
    r"\geq": ">=",
    r"\lt": "<",
    r"\gt": ">",
    "<": "<",
    ">": ">",
}
FLIPPED = {"<=": ">=", ">=": "<=", "<": ">", ">": "<"}


@dataclass(frozen=True)
class Analysis:
    formula: str
    left: object
    right: object
    operator: str
    original: sp.Expr
    expression: sp.Expr
    sign_operator: str
    poles: tuple
    zeros: tuple
    holes: tuple
    points: tuple
    signs: tuple
    solution: object


def roots(value):
    p = polynomial(value)
    if p.is_zero:
        raise UnsupportedCondition("the original denominator is identically zero")
    result = tuple(sorted(set(sp.real_roots(p))))
    if any(r.is_Rational is not True for r in result):
        raise UnsupportedCondition(
            "this reviewed interval family needs rational boundaries"
        )
    return result


def normalize(expression, operator):
    numerator, denominator = sp.fraction(sp.cancel(expression))
    p, q = polynomial(numerator), polynomial(denominator)
    if p.is_zero:
        return sp.Integer(0), operator
    _, p = p.primitive()
    _, q = q.primitive()
    factor = sp.sign(p.LC()) * sp.sign(q.LC())
    return (
        sp.cancel(p.as_expr() / q.as_expr() * factor),
        FLIPPED[operator] if factor < 0 else operator,
    )


def accepts(value, operator):
    sign = sp.sign(value)
    if sign not in (-1, 0, 1):
        raise UnsupportedCondition("the interval sign must be exact")
    return {"<=": sign <= 0, ">=": sign >= 0, "<": sign < 0, ">": sign > 0}[operator]


def interval_signs(expression, points, operator, poles):
    boundaries = (-sp.oo, *points, sp.oo)
    intervals, signs = [], []
    for left, right in pairwise(boundaries):
        sample = (
            sp.Integer(0)
            if left == -sp.oo and right == sp.oo
            else right - 1
            if left == -sp.oo
            else left + 1
            if right == sp.oo
            else (left + right) / 2
        )
        value = expression.subs(X, sample)
        signs.append(int(sp.sign(value)))
        if accepts(value, operator):
            intervals.append(sp.Interval.open(left, right))
    if operator.endswith("="):
        intervals.extend(
            sp.FiniteSet(point)
            for point in points
            if point not in poles and expression.subs(X, point) == 0
        )
    return tuple(signs), sp.Union(*intervals)


def analyze(formula):
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete rational inequality is required")
    readers = [RationalParser(text) for text in (parts[0], parts[2])]
    left, right = [reader.parse() for reader in readers]
    poles = tuple(
        sorted(
            {
                root
                for reader in readers
                for denominator in reader.denominators
                for root in roots(sp.fraction(sp.cancel(denominator))[0])
            }
        )
    )
    original = sp.cancel(left.value - right.value)
    operator = OPERATORS[parts[1]]
    expression, sign_operator = normalize(original, operator)
    numerator, denominator = sp.fraction(expression)
    zeros = roots(numerator) if numerator != 0 else ()
    points = tuple(sorted(set(zeros) | set(poles)))
    signs, solution = interval_signs(expression, points, sign_operator, poles)
    holes = tuple(point for point in poles if denominator.subs(X, point) != 0)
    return Analysis(
        formula,
        left,
        right,
        operator,
        original,
        expression,
        sign_operator,
        poles,
        zeros,
        holes,
        points,
        signs,
        solution,
    )


def set_latex(solution):
    if solution == sp.EmptySet:
        return r"\varnothing"
    if solution == sp.S.Reals:
        return r"\mathbb R"
    if isinstance(solution, sp.Union):
        return r"\cup ".join(set_latex(part) for part in solution.args)
    if isinstance(solution, sp.FiniteSet):
        return r"\{" + ";".join(map(sp.latex, solution)) + r"\}"
    if isinstance(solution, sp.Interval):
        left = "(" if solution.left_open else "["
        right = ")" if solution.right_open else "]"
        return left + sp.latex(solution.start) + ";" + sp.latex(solution.end) + right
    raise UnsupportedCondition("unsupported exact interval answer")
