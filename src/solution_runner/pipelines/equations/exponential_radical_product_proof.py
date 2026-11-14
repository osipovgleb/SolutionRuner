"""Find the real domain first, then zeros and signs as in the source parent."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expression
from .exponential_radical_product import analyze
from .exponential_radical_product_figures import SOURCES, chart
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices
from .rational_inequality_figures import read_formula


def render(a, image):
    html = "<p>Найдём, при каких значениях x подкоренное выражение неотрицательно. Пусть</p>"
    html += line(
        "t="
        + r"\sqrt{"
        + power(a.base, 2 * a.exponent)
        + "}="
        + power(a.base, a.exponent)
        + r",\quad t>0"
    )
    html += line(
        expression(a.radicand, "t")
        + r"\ge0\iff "
        + expression(sp.factor(a.radicand), "t")
        + r"\ge0"
    )
    html += line(choices("t", a.positive_domain))
    html += "<p>Сделаем обратную замену:</p>" + line(
        choices(power(a.base, a.exponent), a.positive_domain)
    )
    html += line(alternatives("x", a.domain, a.endpoint))
    html += "<p>Таким образом, получена область определения исходного неравенства. Решим его методом интервалов. Найдём нули левой части. Первый множитель обращается в нуль при условии:</p>"
    threshold = a.coefficient_stage.zeros[0]
    html += line(expression(a.coefficient, "t") + "=0\\iff t=" + sp.latex(threshold))
    html += line(
        power(a.base, a.exponent)
        + "="
        + sp.latex(threshold)
        + r"\iff x="
        + a.endpoint(a.coefficient_zero)
    )
    html += "<p>Это значение не принадлежит области определения. Нули второго множителя совпадают с нулями подкоренного выражения:</p>"
    html += line(
        expression(a.radicand, "t")
        + "=0\\iff "
        + choices("t", sp.FiniteSet(*a.domain_stage.zeros))
    )
    html += line(alternatives("x", sp.FiniteSet(*a.points), a.endpoint))
    html += (
        "<p>Расставим точки на прямой и определим знаки на области допустимых значений. Между отмеченными точками корень не определён; этот открытый промежуток исключён:</p>"
        + image
    )
    return (
        html
        + "<p>Таким образом, решение исходного неравенства:</p>"
        + line(alternatives("x", a.solution, a.endpoint))
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed exponential-root product parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    image, keys, changes = chart(context, a, generated_solution_assets)
    return repair(
        condition,
        answer,
        solution,
        a.answer,
        render(a, image),
        keys=keys,
        asset_changes=changes,
    )
