"""Compare exact prime-power exponents after selecting one increasing common base."""

from dataclasses import dataclass
from functools import reduce
from math import gcd

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_parser import ExponentialParser
from .rational_inequality import OPERATORS, analyze
from .rational_inequality_methods import terms
from .rational_inequality_parser import polynomial
from .rational_inequality_proof import RELATION


def vector(value):
    if value.is_Rational is not True or value <= 0 or max(value.p, value.q) > 10**6:
        raise UnsupportedCondition(
            "a bounded positive rational prime factorization is required"
        )
    result = dict(sp.factorint(value.p))
    for prime, exponent in sp.factorint(value.q).items():
        result[prime] = result.get(prime, 0) - exponent
    return {p: int(e) for p, e in result.items() if e}


def weight(value, reference):
    actual = vector(value)
    if not actual:
        return sp.Integer(0)
    if set(actual) != set(reference):
        raise UnsupportedCondition(
            "the positive number must be an exact power of the common base"
        )
    ratios = {sp.Rational(actual[p], reference[p]) for p in actual}
    if len(ratios) != 1:
        raise UnsupportedCondition("the prime exponents must have one exact ratio")
    return ratios.pop()


def common_base(bases):
    first = vector(bases[0])
    content = reduce(gcd, map(abs, first.values()))
    primitive = {p: e // content for p, e in first.items()}
    candidate = sp.prod(sp.Integer(p) ** e for p, e in primitive.items())
    if candidate < 1:
        primitive = {p: -e for p, e in primitive.items()}
    weights = [weight(base, primitive) for base in bases]
    if any(w.is_Integer is not True for w in weights):
        raise UnsupportedCondition(
            "the common rational base requires integer prime-vector multiples"
        )
    common = reduce(gcd, (abs(int(w)) for w in weights))
    return sp.prod(sp.Integer(p) ** (e * common) for p, e in primitive.items())


def monomial(node):
    if not node.value.free_symbols and node.value.is_Rational is True:
        return node.value, None
    if node.kind == "exponential":
        base, exponent = (c.value for c in node.children)
        return sp.Integer(1), (base, exponent)
    if node.kind == "multiply":
        c, left = monomial(node.children[0])
        d, right = monomial(node.children[1])
        if (left is None) != (right is None):
            return c * d, left or right
    raise UnsupportedCondition(
        "each term must be one exponential with a rational coefficient"
    )


@dataclass(frozen=True)
class Comparison:
    formula: str
    operator: str
    left: object
    right: object
    powers: tuple
    base: sp.Expr
    exponents: tuple
    stage: object


def compare(formula):
    import re

    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete exponential inequality is required")
    readers = [ExponentialParser(text) for text in (parts[0], parts[2])]
    left, right = [reader.parse() for reader in readers]
    if any(d.free_symbols for reader in readers for d in reader.denominators):
        raise UnsupportedCondition(
            "this exponent-comparison method needs polynomial exponents on the full real line"
        )
    values = []
    constant = sp.Integer(0)
    for sign, node in terms(left) + terms(right, -1):
        coefficient, power = monomial(node)
        if power is None:
            constant += sign * coefficient
        else:
            values.append((sign * coefficient, *power))
    if len(values) == 1 and constant != 0:
        values.append((constant, values[0][1], sp.Integer(0)))
        constant = sp.Integer(0)
    if constant != 0 or len(values) != 2 or values[0][0] * values[1][0] >= 0:
        raise UnsupportedCondition(
            "two exponential terms on opposite sides and no remaining constant are required"
        )
    positive = next(v for v in values if v[0] > 0)
    negative = next(v for v in values if v[0] < 0)
    powers = (positive, (-negative[0], negative[1], negative[2]))
    base = common_base([v[1] for v in powers])
    reference = vector(base)
    exponents = tuple(
        sp.expand(weight(coefficient, reference) + weight(b, reference) * g)
        for coefficient, b, g in powers
    )
    for exponent in exponents:
        if polynomial(exponent).degree() > 2:
            raise UnsupportedCondition(
                "the compared exponents must be at most quadratic"
            )
    operator = OPERATORS[parts[1]]
    stage = analyze(
        sp.latex(exponents[0]) + RELATION[operator] + " " + sp.latex(exponents[1])
    )
    return Comparison(formula, operator, left, right, powers, base, exponents, stage)
