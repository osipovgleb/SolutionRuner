"""Keep the parent's squared-log identity, quadratic replacement and inverse chain."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .logarithm_product_cancellation_proof import logarithm
from .rational_inequality_proof import RELATION


def render(a):
    q = a.quadratic
    inner = logarithm(a.inner_base, "x")
    outer = logarithm(q.base, "-" + inner)
    html = "<p>Из условия следует " + inline("x>0,\\quad -" + inner + ">0")
    html += ". Поэтому в свойстве логарифма квадрата модуль внутреннего логарифма заменяется противоположным ему числом:</p>"
    html += line(
        logarithm(a.original_outer_base, r"\left(" + inner + r"\right)^2")
        + "=2"
        + logarithm(a.original_outer_base, "-" + inner)
    )
    if a.original_outer_base < 1:
        html += "<p>Перейдём к обратному основанию. Логарифм меняет знак, а его квадрат остаётся прежним:</p>"
        html += line(logarithm(a.original_outer_base, "-" + inner) + "=-" + outer)
    html += "<p>Введём замену и решим полученное квадратное неравенство:</p>" + line(
        "z=" + outer
    )
    html += line(expression(q.stage.original, "z") + RELATION[q.operator] + "0")
    html += line(
        expression(sp.factor(q.stage.original), "z") + RELATION[q.operator] + "0"
    )
    html += line(alternatives("z", q.stage.solution))
    html += "<p>Вернёмся к исходной переменной. Основания логарифмов больше единицы; при умножении двойного неравенства на −1 меняются знаки и порядок границ:</p>"
    html += line(alternatives(outer, q.stage.solution))
    positive = sp.Interval(
        -q.solution.end,
        -q.solution.start,
        left_open=q.solution.right_open,
        right_open=q.solution.left_open,
    )
    html += line(alternatives("-" + inner, positive))
    html += line(alternatives(inner, q.solution))
    return html + line(alternatives("x", a.solution, a.endpoint))
