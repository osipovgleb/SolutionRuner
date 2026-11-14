"""Preserve reciprocity and squared-logarithm parents over one proven identity."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices
from .logarithmic_power import analyze
from .rational_inequality_figures import read_formula
from .rational_inequality_proof import RELATION

SOURCES = json.loads(
    (Path(__file__).parent / "assets/logarithmic-inequalities/powers.json").read_text()
)


def ref_log(a, argument):
    return (
        r"\lg\left(" + argument + r"\right)"
        if a.decimal_log
        else logarithm(a.reference, argument)
    )


def power_text(base, exponent):
    text = sp.latex(base)
    if base.is_Integer is not True:
        text = r"\left(" + text + r"\right)"
    return text + "^{" + exponent + "}"


def render(a):
    log_x = ref_log(a, "x")
    second_exponent = (
        a.second_exponent_text.replace(r"\log_{10}", r"\lg")
        if a.decimal_log
        else a.second_exponent_text
    )
    exponent = (
        log_x if a.method == "linear_reciprocity" else r"\left(" + log_x + r"\right)^2"
    )
    term = power_text(a.base, exponent)
    relation = RELATION[a.operator]
    html = "<p>Решение неравенства ищем при условии</p>" + line("x>0")
    if a.method == "linear_reciprocity":
        html += "<p>При этом условии воспользуемся свойством степеней и логарифмов:</p>"
        html += line(
            "x^{"
            + second_exponent
            + "}=x^{"
            + ref_log(a, sp.latex(a.base))
            + "}="
            + term
        )
    else:
        html += "<p>Приведём второе слагаемое к тому же основанию, записав положительный x через его логарифм:</p>"
        html += line(
            "x^{"
            + second_exponent
            + r"}=\left("
            + power_text(a.reference, log_x)
            + r"\right)^{"
            + second_exponent
            + "}="
            + term
        )
    html += "<p>Неравенство принимает вид:</p>"
    html += line(r"2\cdot" + term + relation + sp.latex(a.right))
    html += line(term + relation + power(a.base, a.level))
    html += "<p>Основание показательной функции больше единицы, поэтому сравниваем показатели, сохраняя знак:</p>"
    html += line(exponent + relation + sp.latex(a.level))
    if a.method == "square_coordinate":
        html += line(
            r"\left|" + log_x + r"\right|" + relation + sp.latex(sp.sqrt(a.level))
        )
        html += line(choices(log_x, a.inverse.stage.solution))
    html += "<p>Возвращаясь от логарифма к положительной переменной, получаем:</p>"
    return html + line(alternatives("x", a.inverse.solution))


def build_context_repair_plan(context, *, method, parent_solution_html=""):
    if (
        method not in SOURCES["parents"]
        or hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"][method]
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent for this logarithmic-power method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed logarithmic-power parents have no source figures"
        )
    a = analyze(formula, method)
    return repair(condition, answer, solution, a.answer, render(a))
