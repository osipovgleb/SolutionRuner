"""Replace typed exponential leaves while retaining every rational denominator."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import vector, weight
from .exponential_inequality_quadratic import scaled
from .rational_inequality_parser import X
from .rational_substitution_preimages import excluded_points


def leaves(node):
    if node.kind == "exponential":
        return (node,)
    return tuple(p for child in node.children for p in leaves(child))


def monomial(base, exponent, target_base, target_exponent, variable=X):
    effective = sp.cancel(weight(base, vector(target_base)) * exponent)
    degree = sp.cancel(sp.diff(effective, X) / sp.diff(target_exponent, X))
    offset = sp.cancel(effective - degree * target_exponent)
    if (
        degree.is_Integer is not True
        or abs(degree) > 4
        or offset.is_Rational is not True
    ):
        raise UnsupportedCondition(
            "the substitution needs small integer powers and rational offsets"
        )
    return scaled(sp.Integer(1), target_base, offset) * variable**degree


def substitute(node, base, exponent):
    if node.kind == "exponential":
        b, g = (c.value for c in node.children)
        return sp.latex(monomial(b, g, base, exponent))
    if node.kind == "negative":
        return "-(" + substitute(node.children[0], base, exponent) + ")"
    if node.kind in ("add", "subtract", "multiply", "divide", "power"):
        left, right = [substitute(c, base, exponent) for c in node.children]
        if node.kind == "divide":
            return r"\frac{" + left + "}{" + right + "}"
        if node.kind == "power":
            return "(" + left + ")^{" + right + "}"
        return (
            "("
            + left
            + ")"
            + {"add": "+", "subtract": "-", "multiply": r"\cdot "}[node.kind]
            + "("
            + right
            + ")"
        )
    if node.value.free_symbols:
        raise UnsupportedCondition(
            "ordinary x outside an exponential substitution is not reviewed"
        )
    return sp.latex(node.value)


def original_domains(denominators, base, exponent):
    substitution_poles, original_poles = set(), set()
    variable = sp.Symbol("T", positive=True)
    for d in denominators:
        if d.is_rational_function(X):
            original_poles.update(excluded_points((d,)))
            continue
        replacements = {
            power: monomial(power.base, power.exp, base, exponent, variable)
            for power in d.atoms(sp.Pow)
            if power.exp.has(X)
        }
        converted = d.xreplace(replacements)
        if converted.free_symbols - {variable}:
            raise UnsupportedCondition(
                "each original denominator must have an exact substitution or x domain"
            )
        substitution_poles.update(excluded_points((converted.subs(variable, X),)))
    return substitution_poles, original_poles
