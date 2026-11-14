"""Normalize the factors, find their zeros and apply intervals on the original domain."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expression
from .exponential_log_product import analyze
from .exponential_log_product_figures import SOURCES, chart
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices
from .rational_inequality_figures import read_formula
from .rational_inequality_proof import RELATION


def render(a, image):
    log = logarithm(a.base, sp.latex(a.argument))
    first = power(a.base, a.exponents[0]) + "-" + power(a.base, a.exponents[1])
    second = expression(a.log_polynomial, log)
    html = "<p>Преобразуем неравенство. Приведём основания логарифмов по формуле перехода. Для обратного основания коэффициент равен −1; при возведении в квадрат этот знак исчезает. Постоянные множители показательных функций внесём в их показатели:</p>"
    html += line(
        r"\left("
        + first
        + r"\right)\left("
        + second
        + r"\right)"
        + RELATION[a.operator]
        + "0"
    )
    html += (
        "<p>Область определения задаётся условием положительности аргумента:</p>"
        + line(sp.latex(a.argument) + r">0\iff x>" + sp.latex(-a.shift))
    )
    html += "<p>Найдём нули первого множителя. Основание больше единицы, поэтому равны показатели:</p>"
    html += line(
        power(a.base, a.exponents[0])
        + "="
        + power(a.base, a.exponents[1])
        + r"\iff "
        + sp.latex(a.exponents[0])
        + "="
        + sp.latex(a.exponents[1])
        + r"\iff x="
        + sp.latex(a.shared_zero)
    )
    html += (
        "<p>Этот корень лежит в области определения. Найдём нули второго множителя:</p>"
    )
    html += line(
        second + "=0\\iff " + expression(sp.factor(a.log_polynomial), log) + "=0"
    )
    html += line(choices(log, sp.FiniteSet(0, a.level)))
    html += line(alternatives(sp.latex(a.argument), sp.FiniteSet(1, a.base**a.level)))
    html += line(alternatives("x", sp.FiniteSet(a.shared_zero, a.second_zero)))
    html += "<p>Упорядочим найденные числа. Второй корень больше первого, поскольку основание больше единицы, а второй логарифмический уровень положителен:</p>"
    html += line(
        sp.latex(a.base**a.level)
        + r">1\quad\Longrightarrow\quad "
        + sp.latex(a.second_zero)
        + ">"
        + sp.latex(a.shared_zero)
    )
    html += (
        "<p>Применим метод интервалов на исходной области определения. Первый множитель положителен слева от своего нуля и отрицателен справа. У второго множителя знаки «плюс, минус, плюс» при прохождении его двух нулей. Поэтому знаки произведения на трёх допустимых промежутках — «плюс, плюс, минус». Общий нуль двух множителей отдельно учитываем по строгости исходного сравнения:</p>"
        + image
    )
    return html + line(alternatives("x", a.solution))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed exponential-logarithm product parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    image, keys, changes = chart(context, a)
    return repair(
        condition,
        answer,
        solution,
        a.answer,
        render(a, image),
        keys=keys,
        asset_changes=changes,
    )
