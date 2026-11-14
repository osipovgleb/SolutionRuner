"""Preserve parent positive-factor rationalization or the parent interval chart."""

import hashlib

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_polynomial_product import analyze
from .logarithm_polynomial_product_figures import SOURCES, chart, validate_source
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION
from .rational_inequality_roots import real_roots
from .rational_substitution_preimages import comparison


def product(value, log):
    value_text = sp.latex(value)
    return (value_text if value.is_Mul else r"\left(" + value_text + r"\right)") + log


def factorization(value):
    roots = real_roots(value)
    factors = sp.Mul(*(X - root for root in reversed(roots)), evaluate=False)
    if polynomial(value).LC() != 1:
        factors = sp.Mul(polynomial(value).LC(), factors, evaluate=False)
    if sp.expand(factors - value) != 0:
        raise UnsupportedCondition(
            "the complete quadratic must factor over the reviewed real boundaries"
        )
    return factors


def identities(a):
    log = logarithm(a.base, sp.latex(a.argument))
    html = "<p>Перенесём все члены в левую часть. На исходной области определения перейдём к общему основанию и используем свойство логарифма степени:</p>"
    seen = set()
    for atom, degree, ratio in zip(a.atoms, a.degrees, a.ratios, strict=True):
        key = (atom.base, atom.argument)
        if key in seen or (degree == ratio == 1):
            continue
        seen.add(key)
        power = sp.Pow(a.argument, degree, evaluate=False)
        if degree > 1 and sp.latex(atom.argument) != sp.latex(power):
            html += line(sp.latex(atom.argument) + "=" + sp.latex(power))
        coefficient = sp.Rational(degree, ratio)
        replacement = (
            log if coefficient == 1 else sp.latex(coefficient) + r"\cdot " + log
        )
        html += line(logarithm(atom.base, sp.latex(atom.argument)) + "=" + replacement)
    if a.scale != 1:
        html += (
            "<p>Умножим на положительный общий знаменатель " + str(a.scale) + ":</p>"
        )
    converted = []
    for (degree,), coefficient in polynomial(a.polynomial).terms():
        factor = abs(coefficient) * X**degree
        term = (sp.latex(factor) if factor != 1 else "") + log
        sign = "-" if coefficient < 0 else "+" if converted else ""
        converted.append(sign + term)
    html += line("".join(converted) + RELATION[a.operator] + "0")
    html += line(product(a.polynomial, log) + RELATION[a.operator] + "0")
    html += "<p>Разложим многочлен на множители:</p>"
    return html + line(
        product(factorization(a.polynomial), log) + RELATION[a.operator] + "0"
    )


def reduction(a):
    if a.argument != X:
        raise UnsupportedCondition("the positive-factor parent uses the logarithm of x")
    positive = [
        X - root
        for root in real_roots(a.polynomial)
        if a.domain.is_subset(comparison(X - root, ">").solution) is True
    ]
    if len(positive) != 1:
        raise UnsupportedCondition(
            "exactly one linear factor must be strictly positive on the entire original domain"
        )
    reduced = sp.cancel(a.polynomial / positive[0])
    stage = comparison(reduced * (a.argument - 1), a.operator)
    if stage.solution.intersect(a.domain) != a.solution:
        raise UnsupportedCondition(
            "discarding a positive factor must preserve every original exclusion"
        )
    log = logarithm(a.base, "x")
    html = identities(a)
    html += "<p>На исходной области определения указанный линейный множитель положителен:</p>"
    html += line(choices("x", a.domain))
    html += line(sp.latex(positive[0]) + ">0")
    html += "<p>Разделим на этот положительный множитель:</p>"
    html += line(product(reduced, log) + RELATION[a.operator] + "0")
    html += line(
        product(reduced, r"\left(" + log + "-" + logarithm(a.base, "1") + r"\right)")
        + RELATION[a.operator]
        + "0"
    )
    html += "<p>Знак логарифма по основанию больше единицы совпадает со знаком разности его аргумента и единицы. Применим рационализацию на исходной области:</p>"
    html += system(
        [
            sp.latex(sp.factor(stage.original)) + RELATION[a.operator] + "0",
            choices("x", a.domain),
        ]
    )
    return html + line(choices("x", a.solution))


def interval_chart(a, image):
    html = identities(a)
    if a.domain.is_subset(comparison(a.polynomial, ">").solution) is True:
        html += "<p>На исходной области многочлен положителен, поэтому знак произведения определяется знаком логарифма:</p>"
        html += line(choices("x", a.domain))
        html += line(sp.latex(a.polynomial) + ">0")
    html += image
    zero = real_roots(a.argument - 1)
    if len(zero) != 1:
        raise UnsupportedCondition("one affine logarithm zero is required")
    html += "<p>Заметим, что логарифм обращается в нуль в указанной точке:</p>"
    html += line(
        logarithm(a.base, sp.latex(a.argument))
        + "=0"
        + r"\iff "
        + sp.latex(a.argument)
        + "=1"
        + r"\iff x="
        + sp.latex(zero[0])
    )
    html += "<p>Применим на исходной области определения метод интервалов, как показано на рисунке:</p>"
    html += line(choices("x", a.domain))
    return html + line(choices("x", a.solution))


def build_context_repair_plan(
    context,
    *,
    parent_solution_html="",
    generated_solution_assets=(),
    method="polynomial_log_reduction",
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed polynomial-logarithm parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if condition.get("asset_keys") or BeautifulSoup(
        condition["html"], "html.parser"
    ).find("img"):
        raise UnsupportedCondition("the reviewed conditions have no figures")
    a = analyze(formula)
    if method == "polynomial_log_reduction":
        for asset in content.get("assets", ()):
            validate_source(asset, condition, a, "alternative_child_only")
        html = reduction(a)
        keys = changes = ()
    elif method == "polynomial_log_chart":
        image, keys, changes = chart(context, a, generated_solution_assets)
        html = interval_chart(a, image)
    else:
        raise UnsupportedCondition("unknown polynomial-logarithm parent method")
    return repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
