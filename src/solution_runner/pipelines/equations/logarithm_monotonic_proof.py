"""Preserve exact radical-base comparisons and the required variable-base extension."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_monotonic import RadicalRange, analyze
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/monotonic-range.json"
    ).read_text()
)


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + r"}\left(" + sp.latex(argument) + r"\right)"


def radical_base(a):
    p, q = a.radicals
    r = a.denominator
    H = r**2 + p - q
    square = 4 * r**2 * p
    divisor = sp.gcd(H**2, square)
    root = sp.sqrt(p)
    html = "<p>Заметим, что основание логарифма больше единицы. При последовательных возведениях в квадрат обе сравниваемые части положительны:</p>"
    html += line(
        sp.latex(r) + "-" + sp.latex(root) + ">0" + r",\qquad " + sp.latex(H) + ">0"
    )
    html += line(
        fraction(sp.sqrt(p) + sp.sqrt(q), r)
        + r">1\iff "
        + sp.latex(sp.sqrt(q))
        + ">"
        + sp.latex(r)
        + "-"
        + sp.latex(root)
    )
    html += line(
        sp.latex(q)
        + ">"
        + sp.latex(r**2 + p)
        + "-"
        + sp.latex(2 * r * root)
        + r"\iff "
        + sp.latex(H)
        + "<"
        + sp.latex(2 * r * root)
    )
    html += line(
        sp.latex(H**2)
        + "<"
        + sp.latex(square)
        + r"\iff "
        + sp.latex(H**2 / divisor)
        + "<"
        + sp.latex(square / divisor)
    )
    return html


def constant_proof(a):
    argument = a.offset - a.exponential_base**X
    html = radical_base(a)
    html += "<p>Основание больше единицы, поэтому логарифмическая функция возрастает. Сохраняем положительность аргумента правого логарифма:</p>"
    html += line(
        logarithm(a.base, a.constant)
        + r"\ge "
        + logarithm(a.base, argument)
        + r"\iff "
        + sp.latex(a.constant)
        + r"\ge "
        + sp.latex(argument)
        + ">0"
    )
    power = sp.latex(a.exponential_base) + "^x"
    extra = [r"x\ne" + sp.latex(p) for p in a.poles]
    html += system(
        [
            power + r"\ge " + sp.latex(a.offset - a.constant),
            power + "<" + sp.latex(a.offset),
            *extra,
        ]
    )
    html += "<p>Показательная функция также возрастает, поэтому получаем:</p>"
    html += system(
        ["x" + r"\ge " + a.endpoint(a.lower), "x<" + a.endpoint(a.upper), *extra]
    )
    return html + line(alternatives("x", a.solution, a.endpoint))


def variable_proof(a):
    html = "<p>В этой задаче основание логарифма зависит от x. Применим тот же приём монотонности, отдельно рассмотрев основания больше и меньше единицы. Сначала учтём область определения:</p>"
    extra = [r"x\ne" + sp.latex(p) for p in a.poles if p != a.center]
    html += system(
        [
            sp.latex(a.base) + ">0",
            sp.latex(a.base) + r"\ne1",
            sp.latex(a.argument) + ">0",
            *extra,
        ]
    )
    html += line(alternatives("x", a.domain))
    square = a.square_coefficient * (X - a.center) ** 2 + 1
    html += "<p>Выделим квадрат в аргументе:</p>"
    html += line(sp.latex(a.argument) + "=" + sp.latex(square) + r"\ge1")
    html += "<p>Аргумент равен единице только в точке, где основание также равно единице. Эта точка запрещена. Поэтому на всей области определения аргумент строго больше единицы.</p>"
    for sign, solution in a.cases:
        if sign == 1:
            html += "<p>При основании больше единицы логарифм положителен. Неравенство произведения равносильно неотрицательности первого множителя:</p>"
            rows = [sp.latex(a.base) + ">1", sp.latex(a.coefficient) + r"\ge0"]
        else:
            html += "<p>При основании между нулём и единицей логарифм отрицателен. Первый множитель должен быть неположительным:</p>"
            rows = ["0<" + sp.latex(a.base) + "<1", sp.latex(a.coefficient) + r"\le0"]
        html += system([*rows, *extra]) + line(alternatives("x", solution))
    return (
        html
        + "<p>Объединяя решения обоих случаев, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithm-monotonicity parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed monotonicity group has no source figures"
        )
    a = analyze(formula)
    html = constant_proof(a) if isinstance(a, RadicalRange) else variable_proof(a)
    return repair(condition, answer, solution, a.answer, html)
