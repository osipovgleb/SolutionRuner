"""Certified rational enclosures for exact algebraic roots and real logarithms."""

from fractions import Fraction as F
from functools import lru_cache
from math import isqrt

import sympy as sp

from ..word_problems.common import UnsupportedCondition


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def multiply(a, b):
    products = [x * y for x in a for y in b]
    return min(products), max(products)


@lru_cache(maxsize=512)
def log_rational(q, terms):
    if q <= 0:
        raise UnsupportedCondition("a real logarithm needs a positive argument")
    if q == 1:
        return F(0), F(0)
    if q < 1:
        lo, hi = log_rational(1 / q, terms)
        return -hi, -lo
    shift = 0
    while q >= 2:
        q /= 2
        shift += 1
    if shift > 128:
        raise UnsupportedCondition("the logarithm magnitude exceeds the reviewed range")
    t = (q - 1) / (q + 1)
    total = sum((2 * t ** (2 * j + 1) / (2 * j + 1) for j in range(terms)), F(0))
    remainder = 2 * t ** (2 * terms + 1) / ((2 * terms + 1) * (1 - t * t))
    lo, hi = total, total + remainder
    if shift:
        t = F(1, 3)
        v = sum((2 * t ** (2 * j + 1) / (2 * j + 1) for j in range(terms)), F(0))
        error = 2 * t ** (2 * terms + 1) / ((2 * terms + 1) * (1 - t * t))
        lo += shift * v
        hi += shift * (v + error)
    return lo, hi


@lru_cache(maxsize=3)
def pi_bounds(terms):
    def atan(q):
        total = sum(
            ((-1) ** j * q ** (2 * j + 1) / (2 * j + 1) for j in range(terms)), F(0)
        )
        other = total + (-1) ** terms * q ** (2 * terms + 1) / (2 * terms + 1)
        return min(total, other), max(total, other)

    return add(
        multiply((F(16), F(16)), atan(F(1, 5))),
        multiply((F(-4), F(-4)), atan(F(1, 239))),
    )


def enclose(value, bits=16):
    if value == sp.pi:
        return pi_bounds(bits)

    if value.is_Rational:
        q = F(int(value.p), int(value.q))
        return q, q
    if value.is_Add:
        result = (F(0), F(0))
        for arg in value.args:
            result = add(result, enclose(arg, bits))
        return result
    if value.is_Mul:
        result = (F(1), F(1))
        for arg in value.args:
            result = multiply(result, enclose(arg, bits))
        return result
    if value.func == sp.log:
        lo, hi = enclose(value.args[0], bits)
        return log_rational(lo, bits)[0], log_rational(hi, bits)[1]
    if value.is_Pow:
        lo, hi = enclose(value.base, bits)
        if value.exp == -1:
            if lo <= 0 <= hi:
                raise UnsupportedCondition("a scalar reciprocal crosses zero")
            return 1 / hi, 1 / lo
        if value.exp == sp.Rational(1, 2):
            if lo < 0:
                raise UnsupportedCondition(
                    "a real square root needs a nonnegative argument"
                )
            scale = 2**bits
            low = isqrt(lo.numerator * scale * scale // lo.denominator)
            high = isqrt(hi.numerator * scale * scale // hi.denominator)
            return F(low, scale), F(high, scale) if F(high, scale) ** 2 == hi else F(
                high + 1, scale
            )
        if value.exp.is_Integer and 0 < value.exp <= 8:
            result = (F(1), F(1))
            for _ in range(int(value.exp)):
                result = multiply(result, (lo, hi))
            return result
    raise UnsupportedCondition(
        "the exact interval scalar is outside the reviewed grammar"
    )


def compare(a, b):
    difference = sp.simplify(a - b)
    if difference == 0:
        return 0
    if difference.is_Rational:
        return 1 if difference > 0 else -1
    for bits in (16, 32, 64):
        lo, hi = enclose(a - b, bits)
        if hi < 0:
            return -1
        if lo > 0:
            return 1
    raise UnsupportedCondition(
        "the interval comparison is not separated by certified bounds"
    )
