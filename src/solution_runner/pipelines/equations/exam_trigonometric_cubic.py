"""Expose the common affine factor before solving a cubic trig polynomial."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive


def groupable(p, variable):
    _, factors = sp.factor_list(p, variable)
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        return False
    quadratic = [f for f, _ in factors if sp.degree(f, variable) == 2]
    return len(quadratic) == 1 and quadratic[0].coeff(variable) == 0


def grouped(p, variable, symbol, angle, quadratic_common=False):
    from .exam_trigonometric_proof import formula

    _, factors = sp.factor_list(p, variable, extension=True)
    candidates = [
        f for f, power in factors if power == 1 and sp.degree(f, variable) == 1
    ]
    affine = next(
        (
            f
            for f in candidates
            if sp.simplify(sp.div(p, f, variable)[0].coeff(variable)) == 0
        ),
        candidates[0] if candidates else None,
    )
    if affine is None:
        raise UnsupportedCondition("a cubic grouping needs an affine common factor")
    affine = primitive(affine, (variable,))
    quotient, remainder = sp.div(p, affine, variable)
    if remainder != 0 or sp.degree(quotient, variable) != 2:
        raise UnsupportedCondition(
            "the cubic must split into an affine and quadratic factor"
        )
    if quadratic_common:
        affine, quotient = quotient, affine
    terms = [
        sp.Mul(coef * variable ** power[0], affine, evaluate=False)
        for power, coef in sp.Poly(quotient, variable).terms()
    ]
    expression = sp.Add(*terms, evaluate=False)
    return (
        "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>"
        + line(formula(expression.subs(variable, symbol), angle) + "=0")
        + line(formula((affine * quotient).subs(variable, symbol), angle) + "=0")
    )
