"""Polynomial division and contained-denominator cancellation over one shared pipeline."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_methods import Step, fraction, latex
from .rational_inequality_parser import X, polynomial
from .rational_inequality_polynomial_methods import collect


def difference(a):
    left, lf = collect(a.left)
    right, rf = collect(a.right)
    return sp.expand(left - right), lf + [(-n, d) for n, d in rf]


def sum_text(whole, values):
    pieces = []
    if whole != 0:
        pieces.append(latex(whole))
    for n, d in values:
        if n == 0:
            continue
        negative = n.could_extract_minus_sign()
        pieces.append(("-" if negative else "+") + fraction(-n if negative else n, d))
    return "".join(pieces).removeprefix("+") or "0"


def step(whole, values):
    return Step(
        sum_text(whole, values), sp.cancel(whole + sum(n / d for n, d in values))
    )


def reduced(values):
    return [sp.fraction(sp.cancel(n / d)) for n, d in values]


def divide(whole, values):
    parts = []
    remainders = []
    total = whole
    for n, d in values:
        quotient, remainder = sp.div(n, d, X)
        parts.append("(" + sum_text(quotient, [(remainder, sp.factor(d))]) + ")")
        total += quotient
        remainders.append((remainder, sp.factor(d)))
    text = (latex(whole) + "+" if whole != 0 else "") + "+".join(parts)
    value = sp.cancel(whole + sum(n / d for n, d in values))
    return Step(text, value), sp.expand(total), remainders


def combine_contained(whole, values, *, split):
    for i, (n, d) in enumerate(values):
        if polynomial(d).degree() != 2:
            continue
        for j, (m, e) in enumerate(values):
            if i == j or polynomial(e).degree() != 1:
                continue
            multiplier = sp.cancel(d / e)
            if not multiplier.is_polynomial(X) or polynomial(multiplier).degree() != 1:
                continue
            combined = sp.expand(n + m * multiplier)
            others = [pair for k, pair in enumerate(values) if k not in (i, j)]
            if split:
                shown = [
                    (sp.factor(combined), sp.factor(d)),
                    (-m * multiplier, sp.factor(d)),
                    (m, e),
                    *others,
                ]
            else:
                shown = [
                    (
                        sp.Add(
                            n, sp.Mul(m, multiplier, evaluate=False), evaluate=False
                        ),
                        sp.factor(d),
                    ),
                    *others,
                ]
            return [
                step(whole, shown),
                step(whole, [(sp.factor(combined), sp.factor(d)), *others]),
            ], reduced([(combined, d), *others])
    return [], values


def pipeline(a, *, split=False, require_zero_whole=True):
    whole, values = difference(a)
    steps = []
    if any(polynomial(sp.gcd(n, d)).degree() > 0 for n, d in values):
        steps.append(step(whole, [(sp.factor(n), sp.factor(d)) for n, d in values]))
        values = reduced(values)
        steps.append(step(whole, values))
    expanded, whole, values = divide(whole, values)
    steps.append(expanded)
    if require_zero_whole and whole != 0:
        raise UnsupportedCondition(
            "the extracted polynomial parts must cancel completely"
        )
    steps.append(step(whole, values))
    combined, values = combine_contained(whole, values, split=split)
    steps += combined
    steps.append(step(whole, values))
    denominator = sp.factor(sp.lcm([d for _, d in values]))
    pieces = [sp.Mul(whole, denominator, evaluate=False)] if whole != 0 else []
    pieces.extend(
        sp.Mul(n, sp.cancel(denominator / d), evaluate=False)
        for n, d in values
        if n != 0
    )
    numerator = sp.Add(*pieces, evaluate=False)
    expanded = sp.expand(numerator)
    if polynomial(expanded).degree() > 2:
        raise UnsupportedCondition(
            "the final common numerator must be at most quadratic"
        )
    steps.append(
        Step(fraction(numerator, denominator), sp.cancel(numerator / denominator))
    )
    steps.append(
        Step(fraction(expanded, denominator), sp.cancel(expanded / denominator))
    )
    result = []
    for item in steps:
        if not result or result[-1].text != item.text:
            result.append(item)
    return [], result


def fraction_division(a):
    whole, values = difference(a)
    if (
        whole != 0
        or len(values) != 3
        or len(a.holes) != 1
        or sorted((polynomial(n).degree(), polynomial(d).degree()) for n, d in values)
        not in ([(0, 1), (1, 1), (2, 2)], [(1, 1), (1, 1), (2, 2)])
    ):
        raise UnsupportedCondition(
            "quadratic and affine fractions with cancelling whole parts are required"
        )
    return pipeline(a)


def degree_division(a):
    left, lf = collect(a.left)
    right, rf = collect(a.right)
    if (
        left != 0
        or len(lf) != 1
        or len(rf) != 2
        or len(a.holes) != 1
        or polynomial(lf[0][0]).degree() not in (3, 4)
        or polynomial(lf[0][1]).degree() != 2
        or polynomial(right).degree() not in (1, 2)
        or any(polynomial(n).degree() > 0 or polynomial(d).degree() != 1 for n, d in rf)
    ):
        raise UnsupportedCondition(
            "a cubic or quartic fraction and matching polynomial bound are required"
        )
    return pipeline(a)


def split_cancel(a):
    whole, values = difference(a)
    degrees = sorted(
        (polynomial(n).degree(), polynomial(d).degree()) for n, d in values
    )
    if polynomial(whole).degree() != 1 or len(values) != 2:
        raise UnsupportedCondition(
            "an affine whole part and two original fractions are required"
        )
    if degrees == [(0, 1), (1, 2)] and len(a.holes) == 1:
        return pipeline(a, split=True, require_zero_whole=False)
    if degrees == [(0, 1), (2, 1)] and not a.holes:
        return pipeline(a)
    raise UnsupportedCondition(
        "the source split or polynomial-division variant is required"
    )


METHODS = {
    "fraction_division": fraction_division,
    "degree_division": degree_division,
    "split_cancel": split_cancel,
}
