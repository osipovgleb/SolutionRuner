"""Bounded polynomial coefficients may contain closed square roots, never poles."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_scalar import compare
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import clean


def polynomial(text, variables=(X,)):
    text = clean(text)
    if any(c in text for c in "qrs"):
        # Commands are removed before checking undeclared coefficient placeholders.
        plain = re.sub(r"\\[a-z]+", "", text)
        if any(c in plain for c in "qrs"):
            raise UnsupportedCondition("undeclared polynomial coefficient variables")
    replacements = {}
    for match in list(re.finditer(r"\\sqrt\{([0-9]{1,6})\}", text)):
        raw = match.group()
        if raw not in replacements:
            if len(replacements) >= 3:
                raise UnsupportedCondition(
                    "at most three numeric radical coefficients are supported"
                )
            replacements[raw] = ("qrs"[len(replacements)], sp.sqrt(int(match[1])))
    for raw, (name, _) in replacements.items():
        text = text.replace(raw, name)
    text = re.sub(r"x(?=\()", lambda _: r"x\cdot", text)
    parser = LaurentParser(text)
    value = symbolic(parser.parse())
    value = sp.expand(
        value.subs({sp.Symbol(name, real=True): v for name, v in replacements.values()})
    )
    if (
        parser.nonzero
        or value.free_symbols - set(variables)
        or not value.is_polynomial(*variables)
        or sp.Poly(value, *variables).total_degree() > 6
    ):
        raise UnsupportedCondition(
            "one bounded polynomial without original variable denominators is required"
        )
    return value


def roots(expression):
    expression = sp.expand(expression)
    if expression == 0:
        raise UnsupportedCondition("an identity requires an infinite solution set")
    _, factors = sp.factor_list(expression, X, extension=True)
    found = []
    for factor, _ in factors:
        p = sp.Poly(factor, X)
        if p.degree() not in (1, 2):
            raise UnsupportedCondition(
                "each reviewed factor must be linear or quadratic"
            )
        if p.degree() == 1:
            found.append(sp.simplify(-p.nth(0) / p.nth(1)))
        else:
            a, b, c = p.all_coeffs()
            d = sp.simplify(b * b - 4 * a * c)
            if compare(d, sp.Integer(0)) >= 0:
                found.extend(
                    sp.simplify((-b + sign * sp.sqrt(d)) / (2 * a)) for sign in (-1, 1)
                )
    return tuple(dict.fromkeys(found))
