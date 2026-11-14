"""Retain base cancellation, quadratic substitution and increasing cubic parents."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_variable_comparison import cubic_comparison, quotient_comparison
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/variable-comparison.json"
    ).read_text()
)


def text(value, name="x"):
    return sp.latex(value.subs(X, sp.Symbol(name, real=True)))


def ref_log(a, value, name="x"):
    raw = text(value, name)
    return (
        a.style + r"\left(" + raw + r"\right)"
        if a.style
        else logarithm(a.reference, raw)
    )


def ratio(n, d):
    return r"\frac{" + n + "}{" + d + "}"


def quotient_setup(a):
    A = a.alpha * a.P + a.beta
    B = a.P - a.c
    C = a.P**2
    lg = ref_log(a, a.G)
    la = ref_log(a, A)
    lb = ref_log(a, B)
    lc = ref_log(a, sp.expand(C))
    relation = RELATION[a.operator]
    html = "<p>В левой части перейдём к общему числовому основанию по формуле смены основания:</p>"
    html += line(
        ratio(la + r"\cdot " + lg, lg + r"\cdot " + lb) + relation + ratio(lc, lb)
    )
    html += "<p>Сократить общий множитель можно при положительном исходном основании, отличном от единицы. Сохраним эти ограничения:</p>"
    html += line(sp.latex(a.G) + r">0,\quad " + sp.latex(a.G) + r"\ne1")
    html += line(ratio(la, lb) + relation + ratio(lc, lb))
    html += "<p>Выделим полный квадрат и введём замену, чтобы сравнивать более простые аргументы логарифмов:</p>"
    html += line(sp.latex(sp.expand(C)) + "=" + sp.latex(C))
    html += line("y=" + sp.latex(a.P))
    A = a.alpha * X + a.beta
    B = X - a.c
    C = X**2
    html += line(
        ratio(ref_log(a, A, "y"), ref_log(a, B, "y"))
        + relation
        + ratio(ref_log(a, C, "y"), ref_log(a, B, "y"))
    )
    html += "<p>При y больше указанного значения все аргументы положительны. Нуль логарифма в знаменателе исключаем:</p>"
    html += line("y>" + sp.latex(a.c) + r",\quad y\ne" + sp.latex(a.c + 1))
    numerator = ref_log(a, C, "y") + "-" + ref_log(a, A, "y")
    denominator = ref_log(a, B, "y") + "-" + ref_log(a, sp.S.One, "y")
    html += line(ratio(numerator, denominator) + RELATION[a.stage.operator] + "0")
    return html


def quotient_rationalization(a):
    relation = RELATION[a.stage.operator] + "0"
    html = "<p>Применим рационализацию на исходной области. При общем основании больше единицы знак разности логарифмов совпадает со знаком разности их аргументов:</p>"
    html += system([text(a.stage.original, "y") + relation, "y>" + sp.latex(a.c)])
    n, d = sp.fraction(a.stage.original)
    html += system(
        [
            ratio(text(sp.factor(n), "y"), text(sp.factor(d), "y")) + relation,
            "y>" + sp.latex(a.c),
        ]
    )
    html += "<p>Методом интервалов получаем:</p>" + line(
        choices("y", a.working_solution)
    )
    html += "<p>Вернёмся к исходной переменной. Для каждого промежутка решим соответствующие квадратные неравенства:</p>"
    for branch in a.branches:
        html += system(
            [
                sp.latex(a.P) + RELATION[c.operator] + " " + sp.latex(c.bound)
                for c in branch.conditions
            ]
        )
        html += system(
            [
                sp.latex(sp.factor(c.stage.original)) + RELATION[c.operator] + "0"
                for c in branch.conditions
            ]
        )
        html += system([choices("x", c.stage.solution) for c in branch.conditions])
    html += line(choices("x", a.preimage))
    html += "<p>Пересечём полученное множество с сохранёнными ограничениями исходного основания:</p>"
    html += system(
        [choices("x", a.preimage), sp.latex(a.G) + ">0", sp.latex(a.G) + r"\ne1"]
    )
    return html + line(choices("x", a.solution))


def quotient_note(a):
    A = a.alpha * a.P + a.beta
    B = a.P - a.c
    html = "<p>Примечание. На исходной области переход к числовому основанию можно пояснить также определением логарифма по переменному основанию:</p>"
    original = ratio(logarithm(a.G, sp.latex(A)), logarithm(a.G, sp.latex(B)))
    return html + line(
        original
        + "="
        + logarithm(B, sp.latex(A))
        + "="
        + ratio(ref_log(a, A), ref_log(a, B))
    )


def render_cubic(a):
    html = "<p>Сначала учтём положительность первого аргумента. Она заставляет основание логарифма быть больше единицы:</p>"
    html += line(sp.latex(a.A) + ">0") + line(choices("x", a.first_stage.solution))
    html += "<p>При таком основании логарифм возрастает. Если первый аргумент положителен и не превосходит второго, то второй аргумент также положителен:</p>"
    html += system(
        [sp.latex(a.A) + r"\le " + sp.latex(a.B), choices("x", a.first_stage.solution)]
    )
    difference = sp.Poly(a.B - a.A, X)
    html += system(
        [
            sp.latex(difference.nth(1) * X) + r"\ge " + sp.latex(-difference.nth(0)),
            choices("x", a.first_stage.solution),
        ]
    )
    html += "<p>Разделим на положительный коэффициент и учтём исходное ограничение:</p>"
    html += system(
        [choices("x", a.stage.solution), choices("x", a.first_stage.solution)]
    )
    return html + line(choices("x", a.solution))


def build_context_repair_plan(
    context, *, parent_solution_html="", method="base_cancel_quotient"
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed variable comparison parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition("these variable comparison parents have no figures")
    if method == "base_cancel_quotient":
        a = quotient_comparison(formula)
        html = quotient_setup(a) + quotient_rationalization(a) + quotient_note(a)
    elif method == "increasing_cubic_comparison":
        a = cubic_comparison(formula)
        html = render_cubic(a)
    else:
        raise UnsupportedCondition("unknown variable comparison method")
    return repair(condition, answer, solution, a.answer, html)
