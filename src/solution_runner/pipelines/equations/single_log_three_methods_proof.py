"""Preserve base cases, quotient rationalization and the supplemental product method."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.common import rewrite
from .expression_repair import with_condition_repair
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_single_proof import constraints, normalized_stage, quotient_proof
from .logarithm_single_rationalization import analyze
from .polynomial_logarithm_cases import base_cases
from .rational_inequality_figures import read_formula
from .rational_inequality_proof import RELATION
from .single_log_three_methods_figures import SOURCES, canonical, chart


def case_proof(a):
    base_domain = a.domains[0] - sp.FiniteSet(*a.poles)
    cases = base_cases(a.G, a.A, a.operator, base_domain, a.domains[1], bound=a.bound)
    html = "<p>Первый способ. Рассмотрим два случая, сохраняя исходную область определения:</p>"
    html += system(constraints(a))
    solutions = []
    for index, (sign, operator, values, allowed, solution) in enumerate(
        reversed(cases), 1
    ):
        condition = sp.latex(a.G) + ">1" if sign == 1 else "0<" + sp.latex(a.G) + "<1"
        html += "<p>" + ("Первый" if index == 1 else "Второй") + " случай: "
        html += (
            "логарифмическая функция возрастает.</p>"
            if sign == 1
            else "логарифмическая функция убывает, поэтому знак сравнения меняется.</p>"
        )
        html += line(condition) + line(choices("x", values))
        html += system(
            [
                sp.latex(a.A) + ">0",
                sp.latex(a.A) + RELATION[operator] + sp.latex(a.power),
            ]
        )
        html += line(sp.latex(sp.factor(a.A - a.power)) + RELATION[operator] + "0")
        html += line(choices("x", allowed))
        html += "<p>Пересекаем с рассматриваемым промежутком основания:</p>"
        html += line(choices("x", solution))
        if solution == sp.EmptySet:
            html += "<p>В этом случае решений нет.</p>"
        solutions.append(solution)
    if sp.Union(*solutions) != a.solution:
        raise UnsupportedCondition(
            "both base cases must agree with the complete rationalization"
        )
    return (
        html
        + "<p>Объединяем решения двух случаев:</p>"
        + line(choices("x", a.solution))
    )


def product_proof(a, image):
    html = "<p>Перепишем числовую границу как логарифм соответствующей степени основания и воспользуемся методом рационализации на исходной области:</p>"
    html += line(
        logarithm(a.G, sp.latex(a.A))
        + RELATION[a.operator]
        + logarithm(a.G, sp.latex(a.power))
    )
    html += system(
        [
            sp.latex(sp.Mul(a.G - 1, a.A - a.power, evaluate=False))
            + RELATION[a.operator]
            + "0",
            *constraints(a),
        ]
    )
    html += "<p>Разложим полученное произведение на множители:</p>" + normalized_stage(
        a.product
    )
    html += line(choices("x", a.product.solution))
    if image:
        html += (
            "<p>На рисунке показаны знаки этого произведения до учёта исходных ограничений:</p>"
            + image
        )
    html += "<p>Учтём исходную область определения, включая все исключённые точки:</p>"
    html += line(choices("x", a.domain))
    return html + line(choices("x", a.solution))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed three-method logarithm parent is required"
        )
    (_, original, _, _), _ = read_formula(context)
    prepared, fixed = canonical(context)
    (_, condition, answer, solution), formula = read_formula(prepared)
    if condition.get("asset_keys"):
        raise UnsupportedCondition("the reviewed condition has no figures")
    a = analyze(formula)
    image, keys, changes = chart(prepared, a)
    html = '<section data-content-kind="solution" data-solution-title="Решение">'
    html += case_proof(a) + "<p>Второй способ:</p>" + quotient_proof(a) + "</section>"
    html += '<section data-content-kind="solution" data-solution-title="Приведём другое решение.">'
    html += product_proof(a, image) + "</section>"
    plan = repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
    change = (
        rewrite(original, "condition", "Условие", fixed) if fixed is not None else None
    )
    return with_condition_repair(plan, change)
