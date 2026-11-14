"""Preserve polynomial-base cases and the heterogeneous root quotient's exact interval chart."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_rationalization_proof import system
from .polynomial_base_mixed_figures import SOURCES, chart
from .polynomial_logarithm_cases import PolynomialLogCases, analyze
from .rational_inequality_figures import read_formula
from .rational_inequality_proof import RELATION


def logarithm_proof(a):
    html = "<p>Сохраняем исходную область определения логарифма:</p>"
    html += system(
        [
            sp.latex(a.base) + ">0",
            sp.latex(a.base) + r"\ne1",
            sp.latex(a.argument) + ">0",
        ]
    )
    if a.poles:
        html += line(r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles))
    for sign, operator, base_values, argument_values, solution in a.cases:
        first = sign == -1
        html += (
            "<p>"
            + ("Первый" if first else "Второй")
            + " случай: "
            + (
                "основание между нулём и единицей, функция убывает."
                if first
                else "основание больше единицы, функция возрастает."
            )
            + "</p>"
        )
        condition = "0<" + sp.latex(a.base) + "<1" if first else sp.latex(a.base) + ">1"
        html += line(condition) + line(alternatives("x", base_values))
        html += "<p>Сравним аргумент с единицей, сохраняя его положительность:</p>"
        html += system(
            [
                sp.latex(a.argument) + ">0",
                sp.latex(a.argument) + RELATION[operator] + "1",
            ]
        )
        html += line(
            sp.latex(sp.expand(a.argument - 1))
            + RELATION[operator]
            + "0"
            + r"\iff "
            + sp.latex(sp.factor(a.argument - 1))
            + RELATION[operator]
            + "0"
        )
        html += line(alternatives("x", argument_values))
        if solution == sp.EmptySet:
            html += "<p>Полученные промежутки не пересекаются; в этом случае решений нет.</p>"
        else:
            html += (
                "<p>Пересекаем результат с рассматриваемым промежутком основания и исходной областью:</p>"
                + line(alternatives("x", solution))
            )
    return (
        html
        + "<p>Объединяя решения двух случаев, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def power(base):
    return sp.latex(base) + "^x"


def root_proof(a, image):
    A, B = a.bases
    u, v = a.thresholds
    numerator = (
        "("
        + power(B)
        + "-"
        + sp.latex(v)
        + ")("
        + sp.latex(a.scale)
        + r"\cdot "
        + power(A)
        + "-"
        + sp.latex(a.scale * u)
        + ")"
    )
    denominator = r"\sqrt{" + sp.latex(a.radicand) + "}"
    html = "<p>В этой задаче дано показательное выражение с корнем в знаменателе. Используем произведение положительных оснований и разложим числитель на множители:</p>"
    html += line(power(A * B) + "=" + power(A) + r"\cdot " + power(B))
    html += line(
        r"\frac{"
        + sp.latex(a.numerator)
        + "}{"
        + denominator
        + r"}\ge0\iff\frac{"
        + numerator
        + "}{"
        + denominator
        + r"}\ge0"
    )
    html += image
    html += "<p>Нули числителя получаются из двух показательных уравнений:</p>"
    html += line(
        power(A)
        + "="
        + sp.latex(u)
        + r"\quad\text{или}\quad "
        + power(B)
        + "="
        + sp.latex(v)
    )
    html += line(alternatives("x", sp.FiniteSet(*a.points)))
    html += "<p>Корень находится в знаменателе, поэтому его аргумент должен быть строго положительным. Сохраняем также все исходные запрещённые точки:</p>"
    html += line(sp.latex(a.radicand) + ">0") + line(alternatives("x", a.domain))
    if a.poles:
        html += line(r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles))
    html += "<p>Оба показательных множителя возрастают. Произведение неотрицательно вне промежутка между двумя нулями; сами нули включаются. Пересекаем это множество с исходной областью определения:</p>"
    return html + line(alternatives("x", a.solution))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed polynomial-base case parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    image, keys, changes = chart(context, a)
    html = (
        logarithm_proof(a)
        if isinstance(a, PolynomialLogCases)
        else root_proof(a, image)
    )
    return repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
