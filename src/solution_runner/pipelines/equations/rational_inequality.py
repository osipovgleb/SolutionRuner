"""Exact interval signs with every original pole, including cancelled holes."""

import re
from dataclasses import dataclass
from itertools import pairwise

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_parser import RationalParser, X, polynomial
from .rational_inequality_roots import compare, ordered
from .rational_inequality_roots import real_roots as roots

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
    presentation_method: str = ""


def normalize(expression, operator):
    numerator, denominator = sp.fraction(sp.cancel(expression))
    p, q = polynomial(numerator), polynomial(denominator)
    if p.is_zero:
        return sp.Integer(0), operator
    _, p = p.primitive()
    _, q = q.primitive()
    factor = compare(p.LC(), 0) * compare(q.LC(), 0)
    return (
        sp.cancel(p.as_expr() / q.as_expr() * factor),
        FLIPPED[operator] if factor < 0 else operator,
    )


def accepts(value, operator):
    sign = compare(value, 0)
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
        signs.append(compare(value, 0))
        if accepts(value, operator):
            intervals.append(sp.Interval.open(left, right))
    if operator.endswith("="):
        intervals.extend(
            sp.FiniteSet(point)
            for point in points
            if point not in poles and sp.simplify(expression.subs(X, point)) == 0
        )
    return tuple(signs), sp.Union(*intervals)


def analyze(formula):
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete rational inequality is required")
    readers = [RationalParser(text) for text in (parts[0], parts[2])]
    left, right = [reader.parse() for reader in readers]
    poles = ordered(
        {
            root
            for reader in readers
            for denominator in reader.denominators
            for root in roots(sp.fraction(sp.cancel(denominator))[0])
        }
    )
    original = sp.cancel(left.value - right.value)
    operator = OPERATORS[parts[1]]
    expression, sign_operator = normalize(original, operator)
    numerator, denominator = sp.fraction(expression)
    zeros = roots(numerator) if numerator != 0 else ()
    points = ordered(set(zeros) | set(poles))
    signs, solution = interval_signs(expression, points, sign_operator, poles)
    holes = tuple(
        point for point in poles if sp.simplify(denominator.subs(X, point)) != 0
    )
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
        start, end = (
            sp.factor_terms(value) if value.is_Rational is not True else value
            for value in (solution.start, solution.end)
        )
        return left + sp.latex(start) + ";" + sp.latex(end) + right
    raise UnsupportedCondition("unsupported exact interval answer")
