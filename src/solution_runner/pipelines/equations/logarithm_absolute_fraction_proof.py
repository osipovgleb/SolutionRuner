"""Keep the log-power property and both denominator-sign cases with proven positive factors."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_inequality_proof import absolute
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_absolute_fraction import analyze
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/absolute-fraction.json"
    ).read_text()
)


def logarithm(a, argument=None):
    name = r"\lg" if a.style == r"\lg" else r"\log_{" + sp.latex(a.base) + "}"
    return (
        name
        + r"\left("
        + sp.latex(a.argument if argument is None else argument)
        + r"\right)"
    )


def term(coefficient, log):
    return (
        "" if coefficient == 1 else r"\left(" + sp.latex(coefficient) + r"\right)"
    ) + log


def fraction(coefficient, denominator, log):
    return r"\frac{" + term(coefficient, log) + "}{" + sp.latex(denominator) + "}"


def positive_factor(a, sign, log):
    if sign == 1:
        html = line(
            fraction(
                sp.factor(a.coefficient - a.right_scalar * a.degree), a.denominator, log
            )
            + "="
            + term(a.positive_coefficient, log)
        )
        bound = a.positive_coefficient.subs(X, a.center)
        return (
            html
            + "<p>На рассматриваемом промежутке линейный коэффициент строго положителен:</p>"
            + line(sp.latex(a.positive_coefficient) + ">" + sp.latex(bound) + r"\ge0")
        )
    q = sp.Poly(a.negative_numerator, X)
    center = -q.nth(1) / (2 * q.nth(2))
    minimum = -sp.discriminant(q) / (4 * q.nth(2))
    square = q.nth(2) * (X - center) ** 2 + minimum
    html = "<p>Числитель коэффициента строго положителен при всех действительных x:</p>"
    html += line(sp.latex(a.negative_numerator) + "=" + sp.latex(square) + ">0")
    return (
        html
        + "<p>Знаменатель коэффициента также положителен на рассматриваемом промежутке:</p>"
        + line(sp.latex(-a.denominator) + ">0")
    )


def case(a, sign, solution):
    log = logarithm(a)
    relation = ">" if sign == 1 else "<"
    domain = "x" + relation + sp.latex(a.center)
    numerator = a.coefficient - sign * a.right_scalar * a.degree
    denominator = sign * a.denominator
    html = (
        "<p>Рассмотрим случай "
        + ("положительного" if sign == 1 else "отрицательного")
        + " выражения под модулем:</p>"
    )
    html += line(
        domain
        + r"\quad\Longrightarrow\quad "
        + absolute(a.denominator)
        + "="
        + sp.latex(denominator)
    )
    html += system([fraction(numerator, denominator, log) + r"\ge0", domain])
    html += positive_factor(a, sign, log)
    html += "<p>Делим на строго положительный коэффициент. Логарифм по основанию больше единицы неотрицателен, когда его аргумент не меньше единицы:</p>"
    html += system([log + r"\ge0", domain])
    html += system([sp.latex(a.argument) + r"\ge1", domain])
    html += line(
        sp.latex(a.stage.original)
        + r"\ge0\iff "
        + sp.latex(sp.factor(a.stage.original))
        + r"\ge0"
    )
    html += "<p>Пересекаем результат с рассматриваемым промежутком и исходной областью определения:</p>"
    return html + line(alternatives("x", solution))


def render(a):
    log = logarithm(a)
    html = "<p>Учтём исходную область определения: аргумент первого логарифма положителен, а знаменатели не равны нулю:</p>"
    html += system(
        [
            sp.latex(a.argument) + ">0",
            sp.latex(a.denominator) + r"\ne0",
            *(r"x\ne" + sp.latex(p) for p in a.poles if p != a.center),
        ]
    )
    html += "<p>На этой области противоположный аргумент во втором логарифме возведён в чётную степень, поэтому по свойству логарифма:</p>"
    powered = sp.Pow(-a.argument, a.degree, evaluate=False)
    html += line(
        term(a.right_scalar, logarithm(a, powered))
        + "="
        + term(a.right_scalar * a.degree, log)
    )
    html += line(
        r"\frac{"
        + term(a.coefficient, log)
        + "}{"
        + absolute(a.denominator)
        + r"}\ge "
        + fraction(a.right_scalar * a.degree, a.denominator, log)
    )
    for sign, solution in a.cases:
        html += case(a, sign, solution)
    return (
        html
        + "<p>Объединяя решения двух случаев, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithm-fraction parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed logarithm fractions have no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
