"""Divide by a positive exponential to obtain the same rational quadratic."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition


def normalize(powers, shifted):
    high, middle, last = powers
    first_base, middle_base = high[1], middle[1]
    divisor = sp.cancel(middle_base**2 / first_base)
    base = sp.cancel(first_base / middle_base)
    if divisor <= 0 or divisor == 1 or base <= 0 or base == 1:
        raise UnsupportedCondition(
            "three homogeneous terms need a positive nontrivial ratio and divisor"
        )
    conversion = sp.simplify(
        sp.expand_log(sp.log(last[1])) / sp.expand_log(sp.log(divisor))
    )
    if conversion.is_Rational is not True:
        raise UnsupportedCondition("the third power must have the exact divisor base")
    from .exam_exponential import X

    g = middle[2] if shifted else middle[2] - middle[2].subs(X, 0)
    offsets = (
        sp.expand(high[2] - g),
        sp.expand(middle[2] - g),
        sp.expand(conversion * last[2] - g),
    )
    if any(
        v.free_symbols or v.is_Rational is not True or abs(v) > 100 for v in offsets
    ):
        raise UnsupportedCondition(
            "the three homogeneous exponents must share one polynomial part"
        )
    coefficients = tuple(
        coef * constant**offset
        for (coef, _, _), constant, offset in zip(
            powers, (first_base, middle_base, divisor), offsets
        )
    )
    return base, g, coefficients, (divisor, g)


def proof_prefix(a):
    from ..probability.common import line
    from ..word_problems.math_common import number as n
    from .exam_exponential import terms

    divisor, g = a.divisor
    power = sp.latex(a.base) + "^{" + sp.latex(g) + "}"
    denominator = sp.latex(divisor) + "^{" + sp.latex(g) + "}"
    html = "<p>Приведём уравнение к однородному относительно показательных функций. Разделим обе части на выражение, положительное при любом действительном x:</p>"
    html += line(denominator + ">0")
    powers, _ = terms(a.formula)
    for (coefficient, base, exponent), target, degree in zip(
        powers, a.coefficients, (2, 1, 0)
    ):
        numerator = (
            (n(coefficient) + r"\cdot" if coefficient != 1 else "")
            + n(base)
            + "^{"
            + sp.latex(exponent)
            + "}"
        )
        result = (
            n(target)
            if degree == 0
            else (n(target) + r"\cdot" if target != 1 else "")
            + "("
            + power
            + ")"
            + ("^2" if degree == 2 else "")
        )
        html += line(r"\frac{" + numerator + "}{" + denominator + "}=" + result)
    return html
