"""Keep change-of-base-first parent methods and their final original-base exclusions."""

import hashlib
import json
import re
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rational_substitution import analyze_transformed, inverse
from .logarithm_rational_substitution_proof import (
    common_denominator,
    ordered_alternatives,
)
from .logarithm_variable_substitution import analyze
from .rational_inequality import analyze as rational
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/variable-substitution.json"
    ).read_text()
)


def rename(text, variable):
    replacement = (
        variable
        if re.fullmatch("[a-z]", variable)
        else r"\left(" + variable + r"\right)"
    )
    return re.sub(r"(?<![a-zA-Z])x(?![a-zA-Z])", lambda _: replacement, text)


def identities(a, actual):
    html = ""
    for term in a.terms:
        if term.base.has(X):
            changed = (
                r"\frac{"
                + logarithm(a.base, sp.latex(term.argument))
                + "}{"
                + logarithm(a.base, sp.latex(term.base))
                + "}"
            )
            html += line(term.original + "=" + changed)
            html += line(changed + "=" + rename(term.replacement, actual))
        elif term.argument != X:
            coefficient = (
                sp.Poly(term.argument, X).nth(0)
                if not term.argument.has(X)
                else sp.Poly(term.argument, X).nth(1)
            )
            if term.argument.has(X):
                html += line(
                    term.original
                    + "="
                    + logarithm(a.base, sp.latex(coefficient))
                    + "+"
                    + actual
                )
            html += line(term.original + "=" + rename(sp.latex(term.numerator), actual))
    return html


def rational_steps(stage, name):
    relation = RELATION[stage.operator] + "0"
    html = "<p>Перенесём слагаемые в одну сторону и приведём к общему знаменателю:</p>"
    first, expanded = common_denominator(stage)
    html += line(rename(first, name) + relation)
    if first != expanded:
        html += line(rename(expanded, name) + relation)
    coefficient = sp.cancel(stage.original / stage.expression)
    if coefficient != 1:
        html += (
            "<p>Разделим на "
            + ("отрицательный" if coefficient < 0 else "положительный")
            + " множитель "
            + sp.latex(coefficient)
            + (
                " и изменим знак сравнения:</p>"
                if coefficient < 0
                else ", сохраняя знак сравнения:</p>"
            )
        )
    n, d = sp.fraction(stage.expression)
    html += line(
        rename(fraction(sp.factor(n), sp.factor(d)), name)
        + RELATION[stage.sign_operator]
        + "0"
    )
    return html


def reciprocal_identity(a):
    variables = [t for t in a.terms if t.base.has(X)]
    if (
        len(variables) != 1
        or variables[0].argument.has(X)
        or variables[0].argument == 1
    ):
        raise UnsupportedCondition(
            "the reciprocal parent needs one nonunit constant argument"
        )
    term = variables[0]
    return line(
        term.original
        + r"=\frac{1}{"
        + logarithm(term.argument, sp.latex(term.base))
        + "}"
    )


def render(a, method):
    if method not in ("variable_log_product", "variable_log_reciprocal"):
        raise UnsupportedCondition(
            "one reviewed variable-base substitution method is required"
        )
    name = "y" if method == "variable_log_product" else "z"
    actual = logarithm(a.base, "x")
    html = "<p>Найдём область допустимых значений. Аргументы и основания должны быть положительными, а основания переменных логарифмов — отличными от единицы:</p>"
    html += line(
        "x>0"
        + "".join(
            r",\quad x\ne" + a.endpoint(inverse(a.base, p)) for p in a.stage.poles
        )
    )
    html += "<p>Перейдём к общему основанию по формуле смены основания и используем свойство логарифма произведения:</p>"
    if method == "variable_log_reciprocal":
        html += reciprocal_identity(a)
    html += identities(a, actual)
    html += line(rename(a.transformed, actual))
    left = fraction(
        *[sp.factor(v) for v in sp.fraction(sp.together(a.stage.left.value))]
    )
    initial = left + RELATION[a.stage.operator] + " " + sp.latex(a.stage.right.value)
    html += (
        "<p>Упростим составную дробь на исходной области определения:</p>"
        if method == "variable_log_product"
        else "<p>Упростим правую часть:</p>"
    )
    html += line(rename(initial, actual))
    html += "<p>Сделаем замену:</p>" + line(name + "=" + actual)
    html += line(rename(initial, name))
    simple = rational(initial)
    if sp.cancel(simple.original - a.stage.original) != 0:
        raise UnsupportedCondition(
            "simplifying the displayed quotient must be an exact identity"
        )
    html += rational_steps(simple, name)
    algebra = analyze_transformed(
        a.base, (), sp.latex(a.stage.original) + RELATION[a.stage.operator] + "0"
    )
    html += "<p>Решим рациональное неравенство методом интервалов:</p>"
    html += line(ordered_alternatives(algebra, name))
    html += "<p>Вернёмся к исходной переменной. Логарифм по основанию больше единицы возрастает:</p>"
    html += line(ordered_alternatives(algebra, actual))
    html += line(ordered_alternatives(algebra, "x", mapped=True))
    extra = [
        inverse(a.base, p)
        for p in a.stage.poles
        if algebra.solution.contains(inverse(a.base, p)) is sp.true
    ]
    if extra:
        html += "<p>Из полученного множества исключим исходные запрещённые значения оснований, сохранив ограничения до преобразования составной дроби:</p>"
        html += line(r",\quad ".join("x\\ne" + a.endpoint(p) for p in extra))
        html += line(ordered_alternatives(a, "x", mapped=True))
    return html


def build_context_repair_plan(
    context, *, parent_solution_html="", method="variable_log_product"
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed variable-base parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "these variable-base logarithm parents have no figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a, method))
