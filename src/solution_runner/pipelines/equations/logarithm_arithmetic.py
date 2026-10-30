"""Exact positive logarithms as rational functions of prime logarithms."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .power_arithmetic import factor_base


def checked(value):
    value = sp.cancel(sp.powsimp(value))
    replacements = {}
    for term in value.atoms(sp.Pow):
        if not term.base.free_symbols and term.exp.free_symbols:
            replacements[term] = power(term.base, term.exp)
    if replacements:
        value = sp.cancel(value.xreplace(replacements))
    if sp.count_ops(value) > 200 or any(
        abs(n) > 10**12 for n in value.atoms(sp.Integer)
    ):
        raise UnsupportedCondition("the exact logarithm expression exceeds its bounds")
    if value.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise UnsupportedCondition("undefined logarithm arithmetic")
    return value


def prime_log(prime):
    return sp.Symbol("L" + str(prime), positive=True)


def actual(value):
    return value.xreplace({s: sp.log(int(s.name[1:])) for s in value.free_symbols})


def nonzero(value):
    if value.is_zero is False or actual(value).is_zero is False:
        return
    raise UnsupportedCondition("a logarithmic denominator is zero or unproved nonzero")


def logarithm(value):
    """Expand only positive rational powers; never guess logarithms of sums."""
    if value.free_symbols or value.is_positive is not True:
        raise UnsupportedCondition("a logarithm requires an exact positive argument")
    result = sp.Integer(0)
    for base, power in value.as_powers_dict().items():
        if base.is_Rational is not True or base <= 0 or power.is_Rational is not True:
            raise UnsupportedCondition("unsupported positive logarithm argument")
        for prime, terms in factor_base(base).items():
            result += power * sum(t.value for t in terms) * prime_log(prime)
    return checked(result)


def log_ratio(base, argument):
    denominator = logarithm(base)
    nonzero(denominator)
    return checked(logarithm(argument) / denominator)


def power(base, exponent):
    exponent = checked(exponent)
    if exponent.is_Integer and -1000 <= exponent <= 1000:
        if base == 0 and exponent <= 0:
            raise UnsupportedCondition("zero to a nonpositive power is undefined")
        return base**exponent
    if exponent.is_Rational:
        if abs(exponent) > 1000 or exponent.q > 100:
            raise UnsupportedCondition("the logarithmic power exceeds exact bounds")
        if base.is_positive is not True:
            raise UnsupportedCondition("the logarithmic power needs a positive base")
        return base**exponent
    if base.is_Pow and base.base.is_positive is True:
        return power(base.base, checked(base.exp * exponent))
    expanded = checked(logarithm(base) * exponent)
    denominator = sp.denom(expanded)
    if denominator.free_symbols:
        return sp.Pow(base, exponent, evaluate=False)
    coefficients = (
        sp.Poly(expanded, *sorted(expanded.free_symbols, key=str))
        if expanded.free_symbols
        else None
    )
    if coefficients is None:
        if expanded == 0:
            return sp.Integer(1)
        raise UnsupportedCondition("the power does not reduce to prime logarithms")
    result = sp.Integer(1)
    for powers, coefficient in coefficients.terms():
        if sum(powers) != 1 or coefficient.is_Rational is not True:
            return sp.Pow(base, exponent, evaluate=False)
        if abs(coefficient) > 1000 or coefficient.q > 100:
            raise UnsupportedCondition(
                "the logarithmic prime power exceeds exact bounds"
            )
        symbol = coefficients.gens[powers.index(1)]
        result *= sp.Integer(symbol.name[1:]) ** coefficient
    return result
