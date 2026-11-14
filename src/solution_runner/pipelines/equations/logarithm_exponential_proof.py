"""Keep logarithm properties and the original domain before the quadratic change."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expression
from .inequality_plan import repair
from .logarithm_exponential import analyze
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/exponential.json"
    ).read_text()
)


def render(a):
    exponential = power(a.base, a.exponent)
    argument = exponential + "-" + sp.latex(a.shift)
    positive_power = power(a.constant_argument, a.coefficient)
    right_power = power(a.logarithm_base, a.right)
    product = positive_power + r"\cdot\left(" + argument + r"\right)"
    html = "<p>Воспользуемся свойствами логарифмов. Постоянный аргумент положителен, а исходный переменный аргумент должен быть строго положительным. Объединим логарифмы и запишем правую часть логарифмом с тем же основанием:</p>"
    html += line(
        logarithm(a.logarithm_base, product)
        + r"\le"
        + logarithm(a.logarithm_base, right_power)
    )
    html += "<p>Основание логарифмов больше единицы, поэтому знак при сравнении аргументов сохраняется. Получаем равносильную систему:</p>"
    html += system([argument + ">0", product + r"\le" + right_power])
    html += "<p>Решим второе неравенство системы. Разделим его на положительную показательную функцию и упростим отношение степеней:</p>"
    html += line(
        r"\frac{"
        + positive_power
        + "}{"
        + right_power
        + "}="
        + (sp.latex(1 / a.bound) + r"\cdot " if a.bound != 1 else "")
        + exponential
        + ">0"
    )
    html += "<p>Умножая на положительную постоянную, получаем:</p>"
    html += line(exponential + r"\left(" + argument + r"\right)\le" + sp.latex(a.bound))
    html += "<p>Пусть</p>" + line("y=" + exponential + ">0")
    html += "<p>Тогда имеем квадратное неравенство:</p>"
    html += line(
        expression(a.stage.original, "y")
        + r"\le0\iff"
        + expression(sp.factor(a.stage.original), "y")
        + r"\le0"
    )
    html += line(choices("y", a.stage.solution))
    html += "<p>Учитывая первое неравенство системы, сохраняем строгое ограничение на аргумент исходного логарифма и возвращаемся к x:</p>"
    html += line(choices(exponential, a.positive_solution))
    return html + line(alternatives("x", a.solution, a.endpoint))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithm-exponential parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "this reviewed logarithm-exponential parent has no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
