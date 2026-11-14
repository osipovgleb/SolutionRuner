"""Keep substitution-first and algebra-first parent presentations over shared math."""

import hashlib
import json
import re
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rational_substitution import analyze
from .rational_inequality_division_methods import difference, step
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION, interval_signs_text
from .rational_substitution_preimages import comparison

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/rational-substitution.json"
    ).read_text()
)


def rename(text, variable):
    replacement = variable if variable == "t" else r"\left(" + variable + r"\right)"
    return re.sub(r"(?<![a-zA-Z])x(?![a-zA-Z])", lambda _: replacement, text)


def identities(a, variable):
    html, seen = "", set()
    for term in a.terms:
        if term.original in seen or (term.coefficient == 1 and term.degree == 1):
            continue
        seen.add(term.original)
        actual = rename(sp.latex(term.linear), variable)
        if term.power == 2:
            actual = r"\left(" + actual + r"\right)^2"
        html += line(term.original + "=" + actual)
    return html


def ordered_alternatives(a, name, *, mapped=False):
    rows = [
        alternatives(
            name, image if mapped else source, a.endpoint if mapped else sp.latex
        )
        for source, image in a.images
    ]
    if not rows:
        return r"\varnothing"
    return (
        rows[0]
        if len(rows) == 1
        else r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
    )


def common_denominator(a):
    whole, values = difference(a)
    if not values:
        raise UnsupportedCondition(
            "the parent method needs an explicit rational fraction"
        )
    denominator = sp.lcm([d for _, d in values])
    pieces = [
        (sp.expand(sp.cancel(n * denominator / d)), denominator) for n, d in values
    ]
    if whole != 0:
        pieces.append((sp.expand(whole * denominator), denominator))
    expanded = sp.expand(sum(n for n, _ in pieces))
    for value in (step(0, pieces).value, sp.cancel(expanded / denominator)):
        if sp.cancel(value - a.original) != 0:
            raise UnsupportedCondition(
                "every displayed common-denominator step must be an exact identity"
            )
    return step(0, pieces).text, fraction(expanded, denominator)


def rational_steps(a):
    stage = a.stage
    relation = RELATION[stage.operator] + "0"
    already_factored = (
        stage.left.kind == "divide"
        and stage.left.children[0].kind == "power"
        and stage.right.value == 0
    )
    html = "<p>Разложим знаменатель на множители:</p>"
    if not already_factored:
        first, expanded = common_denominator(stage)
        html = "<p>Приведём слагаемые к общему знаменателю, сохраняя все исходные исключённые значения:</p>"
        html += line(rename(first, "t") + relation)
        if first != expanded:
            html += line(rename(expanded, "t") + relation)
    ratio = sp.cancel(stage.original / stage.expression)
    if ratio != 1:
        html += (
            "<p>Разделим на "
            + ("отрицательный" if ratio < 0 else "положительный")
            + " множитель "
            + sp.latex(ratio)
            + (
                " и изменим знак сравнения:</p>"
                if ratio < 0
                else ", сохраняя знак сравнения:</p>"
            )
        )
    n, d = sp.fraction(stage.expression)
    html += line(
        rename(fraction(sp.factor(n), sp.factor(d)), "t")
        + RELATION[stage.sign_operator]
        + "0"
    )
    positives = positive_quadratics(stage)
    for factor, completed in positives:
        html += "<p>Квадратный множитель числителя положителен при всех действительных t:</p>"
        html += line(rename(sp.latex(factor) + "=" + sp.latex(completed), "t") + ">0")
    if positives:
        reduced = sp.cancel(stage.expression / sp.prod(f for f, _ in positives))
        if comparison(reduced, stage.sign_operator).solution != stage.solution:
            raise UnsupportedCondition(
                "removing positive factors must retain the full rational solution"
            )
        html += line(
            rename(sp.latex(sp.factor(reduced)), "t")
            + RELATION[stage.sign_operator]
            + "0"
        )
    html += "<p>Решим неравенство методом интервалов. Допустимые нули числителя при нестрогом сравнении включаем, а нули исходных знаменателей исключаем:</p>"
    html += line(interval_signs_text(stage))
    return html + line(ordered_alternatives(a, "t"))


def render(a, method):
    if method not in (
        "rational_log_sum",
        "rational_log_square",
        "rational_log_general",
    ):
        raise UnsupportedCondition(
            "one reviewed rational logarithm presentation is required"
        )
    actual = logarithm(a.base, "x")
    substitution = line("t=" + actual + r",\quad x>0")
    html = "<p>Логарифмы определены при x>0. Используем свойства логарифма произведения и степени:</p>"
    if method == "rational_log_sum":
        html += "<p>Введём замену:</p>" + substitution
    expanded = identities(a, "t" if method == "rational_log_sum" else actual)
    html += expanded
    initial = a.transformed
    if method != "rational_log_sum":
        if expanded:
            original = (
                sp.latex(a.stage.left.value)
                + RELATION[a.stage.operator]
                + sp.latex(a.stage.right.value)
            )
            html += line(rename(original, actual))
            initial = original
        html += "<p>Пусть:</p>" + substitution
    html += line(rename(initial, "t"))
    if a.stage.poles:
        html += "<p>Сохраняем ограничения всех исходных знаменателей:</p>"
        html += line(r",\quad ".join("t\\ne" + sp.latex(p) for p in a.stage.poles))
    html += rational_steps(a)
    html += "<p>Вернёмся к исходной переменной. Основание больше единицы, поэтому логарифм возрастает; отдельные допустимые точки также сохраняются:</p>"
    html += line(ordered_alternatives(a, actual))
    return html + line(ordered_alternatives(a, "x", mapped=True))


def build_context_repair_plan(
    context, *, parent_solution_html="", method="rational_log_sum"
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed rational logarithm parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition("these rational logarithm parents have no figures")
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a, method))
