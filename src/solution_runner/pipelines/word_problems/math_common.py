"""Reuse the mathematical-markup reader for complete text-only word questions."""

from fractions import Fraction

import sympy as sp

from ..applied.common import read as read_math
from ..core.numbers import NumberFormatError, format_answer
from .common import UnsupportedCondition


def read(context):
    data = read_math(context)
    if any(s.get("asset_keys") for s in data[:3] if s):
        raise UnsupportedCondition(
            "these word models require text sections without figures"
        )
    return data


def number(value):
    try:
        return format_answer(Fraction(value)).replace(",", "{,}")
    except NumberFormatError:
        return sp.latex(value)


def primitive(expression, variables):
    poly = sp.Poly(expression, *variables).clear_denoms(convert=True)[1].primitive()[1]
    return poly.as_expr() if poly.LC() > 0 else -poly.as_expr()
