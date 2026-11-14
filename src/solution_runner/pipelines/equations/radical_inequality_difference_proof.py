"""Keep the parent's equivalent systems and the two independent sign conditions."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices, system
from .radical_inequality_difference import analyze
from .radical_inequality_difference_figures import SOURCES, chart
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION


def render(a, image):
    html = "<p>На области определения квадратный корень строго возрастает, поэтому разность корней имеет тот же знак, что и разность подкоренных выражений. Это верно и тогда, когда оба корня равны нулю. Перейдём к равносильной системе:</p>"
    difference = (
        r"\left("
        + sp.latex(a.square)
        + r"\right)-\left("
        + sp.latex(a.other)
        + r"\right)"
    )
    html += system(
        [
            sp.latex(a.other) + r"\ge0",
            sp.latex(a.square) + r"\ge0",
            r"\frac{" + difference + "}{" + sp.latex(a.denominator) + r"}\le0",
            *(r"x\ne" + sp.latex(p) for p in a.constraints.excluded),
        ]
    )
    html += "<p>Разложим подкоренные выражения на множители и упростим разность в числителе:</p>"
    html += line(
        sp.latex(a.square)
        + r"-\left("
        + sp.latex(a.other)
        + r"\right)="
        + sp.latex(sp.expand(a.square - a.other))
    )
    ratio = sp.cancel(a.stage.original / a.stage.expression)
    if ratio < 0:
        html += "<p>Выносим отрицательный числовой множитель из числителя и меняем знак сравнения:</p>"
    html += system(
        [
            sp.latex(sp.factor(a.other)) + r"\ge0",
            sp.latex(sp.factor(a.square)) + r"\ge0",
            fraction(
                sp.factor(sp.fraction(a.stage.expression)[0]),
                sp.factor(sp.fraction(a.stage.expression)[1]),
            )
            + RELATION[a.stage.sign_operator]
            + "0",
            *(r"x\ne" + sp.latex(p) for p in a.stage.holes),
        ]
    )
    html += "<p>Из первого неравенства получаем:</p>" + line(
        choices("x", a.other_stage.solution)
    )
    html += "<p>Второе неравенство выполняется при всех действительных значениях переменной, поскольку квадрат неотрицателен. Третье решим методом интервалов, исключив нули исходных знаменателей:</p>"
    html += line(choices("x", a.stage.solution)) + image
    return (
        html
        + "<p>Пересекая полученные множества с сохранением исходных ограничений, получаем множество решений исходного неравенства:</p>"
        + line(choices("x", a.solution))
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed square-root-difference parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    image, keys, changes = chart(context, a, generated_solution_assets)
    return repair(
        condition,
        answer,
        solution,
        a.answer,
        render(a, image),
        keys=keys,
        asset_changes=changes,
    )
