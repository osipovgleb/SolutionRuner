"""Keep the parent's product chart or quotient rationalization over shared math."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_single_figures import SOURCES, chart
from .logarithm_single_rationalization import analyze
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION


def constraints(a):
    return [
        sp.latex(a.G) + ">0",
        sp.latex(a.G) + r"\ne1",
        sp.latex(a.A) + ">0",
        *("x\\ne" + sp.latex(p) for p in a.poles),
    ]


def power_identity(a):
    power = a.G if a.bound == 1 else sp.Pow(a.G, a.bound, evaluate=False)
    return (
        "<p>На исходной области представим числовую границу логарифмом соответствующей степени основания:</p>"
        + line(logarithm(a.G, sp.latex(power)) + "=" + sp.latex(a.bound))
        + line(
            logarithm(a.G, sp.latex(a.A))
            + "-"
            + logarithm(a.G, sp.latex(power))
            + RELATION[a.operator]
            + "0"
        )
    )


def normalized_stage(stage):
    relation = RELATION[stage.operator] + "0"
    html = line(sp.latex(sp.factor(stage.original)) + relation)
    coefficient = sp.cancel(stage.original / stage.expression)
    if coefficient != 1:
        html += (
            "<p>Разделим на "
            + ("положительный" if coefficient > 0 else "отрицательный")
            + " числовой множитель"
            + (
                ", сохраняя знак сравнения:</p>"
                if coefficient > 0
                else ", изменив знак сравнения:</p>"
            )
        )
        html += line(
            sp.latex(sp.factor(stage.expression)) + RELATION[stage.sign_operator] + "0"
        )
    return html


def product_proof(a, image):
    html = (
        power_identity(a)
        if a.bound
        else "<p>Нуль равен логарифму единицы на исходной области определения.</p>"
    )
    html += "<p>Применим метод рационализации, сохраняя положительность основания и аргумента, исключение единичного основания и все исходные полюсы:</p>"
    raw = sp.Mul(a.G - 1, a.A - a.power, evaluate=False)
    html += system([sp.latex(raw) + RELATION[a.operator] + "0", *constraints(a)])
    html += "<p>Упростим разности и разложим произведение на множители:</p>"
    html += line(
        r"\left("
        + sp.latex(a.A)
        + r"\right)-\left("
        + sp.latex(a.power)
        + r"\right)="
        + sp.latex(sp.factor(a.A - a.power))
    )
    html += normalized_stage(a.product)
    html += (
        "<p>Из исходных ограничений получаем область допустимых значений:</p>"
        + line(choices("x", a.domain))
    )
    html += (
        "<p>Методом интервалов решим полученное неравенство и пересечём решение с областью определения. На рисунке сверху показаны знаки выражения, снизу — допустимые значения, а закрашенные столбцы дают пересечение:</p>"
        + image
    )
    return html + line(choices("x", a.solution))


def argument_positivity(a):
    p = polynomial(a.A)
    if p.degree() == 2 and p.LC() > 0 and sp.discriminant(p) < 0:
        completed = (
            p.LC() * sp.Pow(X + p.nth(1) / (2 * p.LC()), 2, evaluate=False)
            + p.nth(0)
            - p.nth(1) ** 2 / (4 * p.LC())
        )
        return "<p>Покажем положительность выражения аргумента:</p>" + line(
            sp.latex(a.A) + "=" + sp.latex(completed) + ">0"
        )
    return (
        "<p>Положительность аргумента учитываем строго:</p>"
        + line(sp.latex(sp.factor(a.A)) + ">0")
        + line(choices("x", a.domains[1]))
    )


def quotient_proof(a):
    html = argument_positivity(a)
    html += "<p>Сохраним ограничения исходного основания и знаменателей:</p>" + system(
        constraints(a)
    )
    html += line(choices("x", a.domain))
    if a.bound:
        html += power_identity(a)
    html += "<p>На этой области применим рационализацию. Сравним аргумент с соответствующей степенью основания и сохраним знак логарифма в знаменателе:</p>"
    html += line(fraction(a.A - a.power, a.G - 1) + RELATION[a.operator] + "0")
    n, d = sp.fraction(sp.together(a.A - a.power))
    u, v = sp.fraction(sp.together(a.G - 1))
    html += line(
        fraction(sp.factor(n * v), sp.factor(d * u)) + RELATION[a.operator] + "0"
    )
    html += (
        "<p>Сократим общие множители только при сохранённых исходных исключениях:</p>"
    )
    html += normalized_stage(a.quotient)
    html += "<p>Решим рациональное неравенство методом интервалов:</p>" + line(
        choices("x", a.quotient.solution)
    )
    html += "<p>Учтём все исходные ограничения, включая исключённые точки после сокращений:</p>"
    return html + line(choices("x", a.solution))


def build_context_repair_plan(
    context,
    *,
    parent_solution_html="",
    generated_solution_assets=(),
    method="single_log_product",
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed single-log rationalization parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    if method == "single_log_product":
        image, keys, changes = chart(context, a, generated_solution_assets)
        html = product_proof(a, image)
    elif method == "single_log_quotient":
        if content.get("assets"):
            raise UnsupportedCondition("this quotient parent has no figures")
        keys = changes = ()
        html = quotient_proof(a)
    else:
        raise UnsupportedCondition("unknown single-log rationalization method")
    return repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
