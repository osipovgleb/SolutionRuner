"""Retain division, grouping and common-factor steps from the reviewed parents."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_common_base import vector, weight
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic import scaled
from .exponential_inequality_quadratic_proof import expression, factor_step, membership
from .rational_inequality import FLIPPED
from .rational_inequality_parser import polynomial
from .rational_inequality_proof import RELATION


def sum_terms(terms):
    result = ""
    for c, text in terms:
        if c == 0:
            continue
        sign = "-" if c < 0 else "+" if result else ""
        coefficient = sp.latex(abs(c))
        result += sign + (
            (coefficient + r"\cdot " if abs(c) != 1 else "") + text
            if text
            else coefficient
        )
    return result or "0"


def monotonic(base):
    return (
        "<p>Основание "
        + inline(sp.latex(base) + ">1")
        + ", поэтому показательная функция возрастает.</p>"
    )


def homogeneous(a):
    if not a.divisor or len(a.stage.zeros) != 2:
        raise UnsupportedCondition(
            "the homogeneous parent needs two real quadratic roots and a positive divisor"
        )
    divisor, exponent = a.divisor
    denominator = power(divisor, exponent)
    actual = power(a.base, a.exponent)
    html = line(a.formula)
    html += (
        "<p>Разделим обе части неравенства на положительное при любом действительном x выражение "
        + inline(denominator)
        + ", не меняя знака неравенства:</p>"
    )
    html += line(denominator + ">0")
    ratios = []
    for c, b, g in a.powers:
        if g == exponent:
            text = power(sp.cancel(b / divisor), g) if b != divisor else ""
        else:
            text = r"\frac{" + power(b, g) + "}{" + denominator + "}"
        ratios.append((c, text))
    html += line(sum_terms(ratios) + RELATION[a.operator] + "0")
    html += line(expression(a.stage.original, actual) + RELATION[a.operator] + "0")
    html += "<p>Сделаем замену " + inline("z=" + actual + ">0") + ". Получаем:</p>"
    html += line(expression(a.stage.original, "z") + RELATION[a.operator] + "0")
    html += factor_step(a, a.stage.original, "z")
    html += line(membership("z", a.stage.solution))
    html += "<p>Учитывая положительность z и возвращаясь к исходной переменной, получаем:</p>"
    html += line(membership("z", a.positive_solution))
    html += line(membership(actual, a.positive_solution))
    html += monotonic(a.base)
    return html + line(r"x\in " + a.answer)


def collected(a):
    coefficient = dict(a.coefficients)[1]
    bound = -a.constant / coefficient
    if coefficient == 0 or bound.is_positive is not True or len(a.back) != 1:
        raise UnsupportedCondition(
            "the collected-power parent needs one positive logarithmic bound"
        )
    actual = power(a.base, a.exponent)
    effective = [sp.expand(weight(b, vector(a.base)) * g) for _, b, g in a.powers]
    values = [
        scaled(c, a.base, g - a.exponent) for (c, _, _), g in zip(a.powers, effective)
    ]
    html = line(a.formula) + "<p>Вынесем общую степень за скобки:</p>"
    html += line(
        actual
        + r"\left("
        + sum_terms((c, "") for c in values)
        + r"\right)"
        + RELATION[a.operator]
        + sp.latex(-a.constant)
    )
    html += line(
        sum_terms(((coefficient, actual),))
        + RELATION[a.operator]
        + sp.latex(-a.constant)
    )
    negative = coefficient < 0
    html += (
        "<p>Разделим обе части на "
        + ("отрицательное" if negative else "положительное")
        + " число "
        + inline(sp.latex(coefficient))
        + "; знак неравенства "
        + ("меняется" if negative else "сохраняется")
        + ":</p>"
    )
    operator = FLIPPED[a.operator] if negative else a.operator
    html += line(actual + RELATION[operator] + sp.latex(bound))
    html += monotonic(a.base)
    value = a.back[0][1]
    log = (
        sp.latex(value)
        if value.is_Rational
        else r"\log_{" + sp.latex(a.base) + "}(" + sp.latex(bound) + ")"
    )
    html += line(sp.latex(a.exponent) + RELATION[operator] + log)
    slope = polynomial(a.exponent).nth(1)
    if slope < 0:
        html += "<p>При делении на отрицательный коэффициент при x знак неравенства меняется.</p>"
    return html + line(r"x\in " + a.answer)


def grouped(a):
    first, second = a.bases
    u, v = a.bounds
    left, right = power(first, a.exponent), power(second, a.exponent)
    difference = r"\left(" + sum_terms(((1, right), (-v, ""))) + r"\right)"
    first_difference = r"\left(" + sum_terms(((1, left), (-u, ""))) + r"\right)"
    original = (
        sum_terms((c, power(b, g)) for c, b, g in a.powers) + "+" + sp.latex(a.constant)
    )
    html = (
        line(a.formula)
        + "<p>Заметим, что степень произведения равна произведению степеней. Сгруппируем слагаемые и вынесем общий множитель:</p>"
    )
    html += line(
        original
        + "="
        + sum_terms(((1, left + r"\cdot " + right), (-v, left), (-u, difference)))
    )
    html += line(
        sum_terms(((1, left + r"\cdot " + difference), (-u, difference)))
        + "="
        + first_difference
        + r"\cdot "
        + difference
    )
    html += line(first_difference + r"\cdot " + difference + RELATION[a.operator] + "0")
    powers = [power(base, root) for base, root in zip(a.bases, a.roots)]
    html += line(
        r"\left("
        + left
        + "-"
        + powers[0]
        + r"\right)\left("
        + right
        + "-"
        + powers[1]
        + r"\right)"
        + RELATION[a.operator]
        + "0"
    )
    html += "<p>Оба основания больше единицы. Поэтому каждый показательный множитель имеет тот же знак, что и разность его показателей. Заменяя множители выражениями с теми же знаками, получаем равносильное неравенство:</p>"
    html += line(sp.latex(a.stage.original) + RELATION[a.operator] + "0")
    html += line(sp.latex(sp.factor(a.stage.original)) + RELATION[a.operator] + "0")
    return html + line(membership("x", a.solution))


RENDERS = {
    "homogeneous": homogeneous,
    "collected_power": collected,
    "grouped_product": grouped,
}
