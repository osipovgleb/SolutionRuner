"""Shared exact factor-log identities with the parent's sum or product presentation."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_reduction_proof import sum_terms
from .logarithm_arithmetic import log_ratio
from .logarithm_product_cancellation_proof import logarithm
from .rational_inequality import FLIPPED
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION
from .rational_substitution_preimages import comparison


def factored(argument):
    n, d = sp.factor(argument.numerator), sp.factor(argument.denominator)
    return sp.latex(n) if d == 1 else fraction(n, d)


def domain(a):
    html = "<p>Найдём значения x, при которых определены все исходные логарифмы:</p>"
    html += line(
        r"\begin{cases}"
        + r"\\".join(arg.raw + ">0" for arg in a.arguments)
        + r"\end{cases}"
    )
    html += line(
        r"\begin{cases}"
        + r"\\".join(factored(arg) + ">0" for arg in a.arguments)
        + r"\end{cases}"
    )
    return html + line(alternatives("x", a.domain))


def positive(a, value):
    return a.domain - comparison(value, ">").solution == sp.EmptySet


def factor_log(a, factor):
    text = (
        sp.latex(factor)
        if positive(a, factor)
        else r"\left|" + sp.latex(factor) + r"\right|"
    )
    return logarithm(a.base, text)


def reduced_level(a):
    scalar = log_ratio(a.base, a.scalar)
    if scalar.is_Rational is not True:
        raise UnsupportedCondition(
            "this parent needs an exact rational residual logarithm level"
        )
    return (-a.constant - scalar) / a.multiplier


def final_stage(a, stage, image=""):
    n, d = sp.fraction(stage.expression)
    positive_factors = positive_quadratics(stage)
    positive_set = {factor for factor, _ in positive_factors}
    retained = [f**k for f, k in sp.factor_list(n)[1] if f in positive_set]
    remaining = sp.cancel(n / sp.prod(retained))
    n = sp.Mul(real_factor(remaining, stage.zeros), *retained, evaluate=False)
    html = line(
        (sp.latex(n) if d == 1 else fraction(n, sp.factor(d)))
        + RELATION[stage.operator]
        + "0"
    )
    for factor, completed in positive_factors:
        html += "<p>Квадратный множитель положителен при всех действительных x и не меняет знак:</p>"
        html += line(sp.latex(factor) + "=" + sp.latex(completed) + ">0")
    html += "<p>Решим полученное неравенство и пересечём решение с исходной областью определения:</p>"
    return html + image + line(alternatives("x", a.solution))


def render_sum(a):
    html = domain(a)
    html += (
        "<p>На этой области приведём логарифмы к основанию "
        + inline(sp.latex(a.base))
        + ". Для обратных оснований логарифмы противоположны. Разложим аргументы на множители; если множитель может быть отрицательным, сохраняем его модуль:</p>"
    )
    terms = []
    for argument, weight in zip(a.arguments, a.weights, strict=True):
        inner = [(sp.Integer(k), factor_log(a, f)) for f, k in argument.factors]
        if abs(argument.coefficient) != 1:
            value = log_ratio(a.base, abs(argument.coefficient))
            if value.is_Rational is not True:
                raise UnsupportedCondition(
                    "this factor expansion needs rational constant logarithms"
                )
            inner.append((value, ""))
        terms.append((weight, r"\left(" + sum_terms(inner) + r"\right)"))
    terms.append((a.constant, ""))
    html += line(sum_terms(terms) + RELATION[a.operator] + "0")
    residual = factor_log(a, a.reduced)
    constant = log_ratio(a.base, a.scalar) + a.constant
    html += "<p>Сократим одинаковые логарифмические слагаемые и решим оставшееся неравенство:</p>"
    html += line(
        sum_terms([(a.multiplier, residual), (constant, "")])
        + RELATION[a.operator]
        + "0"
    )
    log_operator = a.operator if a.multiplier > 0 else FLIPPED[a.operator]
    html += line(residual + RELATION[log_operator] + sp.latex(reduced_level(a)))
    argument = (
        sp.latex(a.reduced)
        if positive(a, a.reduced)
        else r"\left|" + sp.latex(a.reduced) + r"\right|"
    )
    html += "<p>При переходе от логарифма к аргументу учитываем монотонность основания и сохраняем ОДЗ:</p>"
    html += line(
        argument + RELATION[a.reduced_operator] + sp.latex(sp.sqrt(a.threshold_squared))
    )
    stage = (
        comparison(a.reduced - sp.sqrt(a.threshold_squared), a.reduced_operator)
        if positive(a, a.reduced)
        else a.stage
    )
    if stage.solution.intersect(a.domain) != a.solution:
        raise UnsupportedCondition(
            "the displayed residual comparison must preserve the full source solution"
        )
    return html + final_stage(a, stage)


def uncancelled_product(a):
    numerator, denominator = [], []
    for argument, weight in zip(a.arguments, a.weights, strict=True):
        for factor, degree in argument.factors:
            exponent = weight * degree
            if exponent.is_Integer is not True:
                raise UnsupportedCondition(
                    "this product parent needs integer argument factor powers"
                )
            text = (
                r"\left("
                + sp.latex(factor)
                + r"\right)"
                + ("^{" + str(abs(exponent)) + "}" if abs(exponent) != 1 else "")
            )
            (numerator if exponent > 0 else denominator).append(text)
    n, d = "".join(numerator) or "1", "".join(denominator)
    return r"\frac{" + n + "}{" + d + "}" if d else n


def render_product(a, image=""):
    if (
        a.base <= 1
        or a.scalar != 1
        or a.multiplier.is_Integer is not True
        or a.multiplier <= 0
        or a.multiplier % 2
    ):
        raise UnsupportedCondition(
            "the reviewed product parent needs a positive even residual power and increasing base"
        )
    html = domain(a)
    html += "<p>Для таких x объединим логарифмы по формулам суммы, разности и степени. Сохраняем все ограничения исходных знаменателей:</p>"
    html += line(
        sum_terms(
            [
                (w, logarithm(a.base, factored(arg)))
                for w, arg in zip(a.weights, a.arguments, strict=True)
            ]
        )
        + RELATION[a.operator]
        + sp.latex(-a.constant)
    )
    product = sp.Pow(sp.factor(a.reduced), a.multiplier, evaluate=False)
    html += line(
        logarithm(a.base, uncancelled_product(a))
        + "="
        + logarithm(a.base, sp.latex(product))
    )
    html += "<p>Основание больше единицы. Остаточная степень чётная, поэтому на исходной области можно перейти к квадрату, не теряя отрицательные значения множителей:</p>"
    html += line(
        sp.latex(product) + RELATION[a.operator] + sp.latex(a.base ** (-a.constant))
    )
    if a.multiplier != 2:
        html += line(
            sp.latex(sp.Pow(sp.factor(a.reduced), 2, evaluate=False))
            + RELATION[a.reduced_operator]
            + sp.latex(a.threshold_squared)
        )
    return html + final_stage(a, a.stage, image)
