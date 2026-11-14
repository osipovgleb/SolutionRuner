"""Read two whole log fractions and retain an even argument power without expansion."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_inequality_input import AbsoluteParser
from .logarithm_rationalization_input import complete_log, fraction_parts
from .power_arithmetic import ScalarParser, balanced, clean
from .rational_inequality_parser import RationalParser, polynomial


def fraction(text):
    text = clean(text)
    if not text.startswith(r"\frac"):
        raise UnsupportedCondition("one whole outer fraction is required")
    numerator, index = balanced(text, 5)
    denominator, index = balanced(text, index)
    if index != len(text):
        raise UnsupportedCondition("the complete right fraction must be recognized")
    return numerator, denominator


def argument(raw, denominators):
    if raw.startswith("("):
        inside, end = balanced(raw, 0, "(", ")")
        if raw[end : end + 2] == "^{":
            exponent, last = balanced(raw, end + 1)
            degree = ScalarParser(exponent).parse()
            if (
                last != len(raw)
                or degree.is_Integer is not True
                or degree not in (2, 4, 6, 8)
            ):
                raise UnsupportedCondition(
                    "one bounded even logarithm-argument power is required"
                )
            base = RationalParser(inside, denominators).parse().value
            if polynomial(base).degree() != 2:
                raise UnsupportedCondition(
                    "the even power must have a whole quadratic base"
                )
            return sp.Pow(base, degree, evaluate=False)
    return RationalParser(raw, denominators).parse().value


def numerator(text, denominators):
    starts = [i for token in (r"\log_", r"\lg") if (i := text.find(token)) >= 0]
    if not starts:
        raise UnsupportedCondition("one complete logarithm must end each numerator")
    index = min(starts)
    prefix = text[:index]
    for token in (r"\cdot", r"\times", "*"):
        if prefix.endswith(token):
            prefix = prefix[: -len(token)]
            if not prefix:
                raise UnsupportedCondition(
                    "a multiplication sign needs its complete coefficient"
                )
            break
    if prefix:
        if prefix.startswith("("):
            _, end = balanced(prefix, 0, "(", ")")
            whole = end == len(prefix)
        else:
            whole = re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", prefix) is not None
        if not whole:
            raise UnsupportedCondition(
                "the coefficient must be one whole parenthesized polynomial or scalar"
            )
        coefficient = RationalParser(prefix, denominators).parse().value
    else:
        coefficient = sp.Integer(1)
    atom, base, style = complete_log(
        text[index:], lambda raw: argument(raw, denominators)
    )
    return coefficient, atom.argument, base, style


def read(formula):
    n, d, right, operator = fraction_parts(formula)
    rn, rd = fraction(right)
    denominators = []
    first = numerator(n, denominators)
    second = numerator(rn, denominators)
    values = {}
    left = AbsoluteParser(d, denominators, values=values).parse()
    denominator = RationalParser(rd, denominators).parse().value
    if len(values) != 1 or left.kind != "absolute":
        raise UnsupportedCondition("the complete left denominator must be one modulus")
    modulus = next(iter(values.values()))
    if sp.expand(modulus - denominator) != 0:
        raise UnsupportedCondition(
            "both complete denominators must share the same affine expression"
        )
    return first, second, denominator, tuple(denominators), operator
