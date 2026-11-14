"""Preserve the two parents' denominator reduction and absolute-value substitution."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_inequality import analyze
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .inequality_plan import repair
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction

SOURCES = json.loads(
    (Path(__file__).parent / "assets/absolute-inequalities/parents.json").read_text()
)


def absolute(argument):
    return r"\left|" + sp.latex(argument) + r"\right|"


def alternative_rows(rows):
    return line(r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right.")


def quotient(a):
    first, second = a.inverse_factors
    numerator = sp.expand(second - first)
    html = "<p>Приведём разность обратных выражений к общему знаменателю:</p>"
    html += line(
        fraction(1, first)
        + "-"
        + fraction(1, second)
        + "="
        + fraction(numerator, sp.factor(a.denominator))
    )
    html += "<p>Преобразуем исходное неравенство, сохраняя все ограничения его знаменателей:</p>"
    html += line(
        fraction(a.bound, a.denominator**2)
        + r"\le"
        + fraction(sp.Abs(a.argument, evaluate=False), a.denominator**2)
    )
    html += line(
        r"\frac{"
        + absolute(a.argument)
        + "-"
        + sp.latex(a.bound)
        + "}{"
        + sp.latex(sp.Pow(a.denominator, 2, evaluate=False))
        + r"}\ge0"
    )
    html += system(
        [
            *(r"x\ne" + sp.latex(p) for p in a.poles),
            absolute(a.argument) + r"\ge" + sp.latex(a.bound),
        ]
    )
    html += "<p>Решим неравенство с модулем как совокупность двух неравенств:</p>"
    html += alternative_rows(
        [
            sp.latex(a.argument - a.bound) + r"\ge0",
            sp.latex(a.argument + a.bound) + r"\le0",
        ]
    )
    html += alternative_rows([alternatives("x", s.solution) for s in a.branches])
    return (
        html
        + "<p>Исключая из полученного набора все исходные запрещённые точки, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def substitution(a):
    html = "<p>Перенесём всё влево и выделим квадрат, равный квадрату аргумента модуля:</p>"
    html += line(
        sp.latex(sp.expand(a.argument**2))
        + "-"
        + sp.latex(a.bound)
        + absolute(a.argument)
        + r"<0\iff\left("
        + sp.latex(a.argument)
        + r"\right)^2-"
        + sp.latex(a.bound)
        + absolute(a.argument)
        + "<0"
    )
    html += "<p>Сделаем замену:</p>" + line(
        "t=" + absolute(a.argument) + r",\quad t\ge0"
    )
    html += "<p>Получаем квадратное неравенство:</p>" + line(
        expression(a.substitution_stage.original, "t")
        + r"<0\iff"
        + expression(sp.factor(a.substitution_stage.original), "t")
        + "<0"
    )
    html += line(alternatives("t", a.substitution_stage.solution))
    html += "<p>Вернёмся к исходной переменной. Модуль должен быть строго положительным и меньше найденной верхней границы:</p>"
    html += line("0<" + absolute(a.argument) + "<" + sp.latex(a.bound))
    html += alternative_rows(
        [
            "0<" + sp.latex(a.argument) + "<" + sp.latex(a.bound),
            "-" + sp.latex(a.bound) + "<" + sp.latex(a.argument) + "<0",
        ]
    )
    if a.poles:
        html += "<p>Сохраняем также исходные запрещённые точки:</p>" + line(
            r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles)
        )
    return html + line(alternatives("x", a.solution))


def build_context_repair_plan(context, *, method, parent_solution_html=""):
    if (
        method not in SOURCES["parents"]
        or hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"][method]
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent for this absolute-inequality method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "these absolute-inequality parents have no source figures"
        )
    a = analyze(formula, method)
    html = quotient(a) if method == "squared_quotient" else substitution(a)
    return repair(condition, answer, solution, a.answer, html)
