"""Keep exact logarithmic levels inside quadratic-root labels."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_scalar import compare
from .exponential_inequality_common_base import vector
from .logarithm_arithmetic import log_ratio, prime_log
from .rational_inequality_parser import X


def logarithm_level(base, argument, value):
    if value.is_Rational:
        return value, {}
    factors = vector(base)
    if len(factors) == 1 and argument.is_Rational:
        prime, degree = next(iter(factors.items()))
        symbolic = log_ratio(base, argument)
        replacements = {prime_log(prime): sp.Integer(1)}
        labels = {}
        for symbol in symbolic.free_symbols - {prime_log(prime)}:
            p = int(symbol.name[1:])
            marker = sp.Symbol("Q" + str(p), positive=True)
            replacements[symbol] = degree * marker
            labels[marker] = r"\log_{" + sp.latex(base) + "}(" + str(p) + ")"
        return sp.expand(symbolic.xreplace(replacements)), labels
    marker = sp.Symbol("Q", real=True)
    return marker, {
        marker: r"\log_{" + sp.latex(base) + "}(" + sp.latex(argument) + ")"
    }


def scalar_text(value, labels):
    text = sp.latex(value)
    for marker, label in labels.items():
        text = text.replace(sp.latex(marker), label)
    return text


def level_text(base, argument, value):
    symbolic, labels = logarithm_level(base, argument, value)
    return scalar_text(symbolic, labels)


def root_text(a, root):
    if not root.has(sp.log):
        return sp.latex(root)
    p = sp.Poly(a.exponent, X)
    leading, linear, _constant = p.all_coeffs()
    center = -linear / (2 * leading)
    extreme = p.eval(center)
    for t, value, branch in a.back:
        if any(root == r or sp.simplify(root - r) == 0 for r in branch):
            symbolic, labels = logarithm_level(a.base, t, value)
            sign = compare(root, center)
            expression = center + sign * sp.sqrt((symbolic - extreme) / leading)
            return scalar_text(expression, labels)
    raise UnsupportedCondition(
        "the logarithmic endpoint must have a certified inverse root"
    )
