"""Keep the parent's equivalent systems and its note on the redundant domain."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices, system
from .radical_inequality_comparison import analyze
from .radical_inequality_figures import SOURCES, chart
from .rational_inequality_figures import read_formula


def root(value):
    return r"\sqrt{" + sp.latex(value) + "}"


def render(a, image):
    L, C, B = map(sp.latex, (a.left, a.numerator, a.denominator))
    html = "<p>Имеем:</p>"
    html += line(
        root(a.left) + r"<\frac{" + root(a.numerator) + "}{" + root(a.denominator) + "}"
    )
    html += "<p>Корень в знаменателе должен быть положительным. Умножая на него обе части, перейдём к равносильной системе:</p>"
    html += system(
        [
            root(a.left) + r"\cdot" + root(a.denominator) + "<" + root(a.numerator),
            L + r"\ge0",
            B + ">0",
            *(r"x\ne" + sp.latex(p) for p in a.poles),
        ]
    )
    product = sp.Mul(a.left, a.denominator, evaluate=False)
    html += "<p>Объединим корни в левой части. Сравнивая неотрицательные величины, получаем:</p>"
    html += line(root(a.numerator) + ">" + root(product))
    html += system([C + ">" + sp.latex(product), choices("x", a.domain)])
    html += "<p>Перенесём произведение в левую часть и раскроем скобки:</p>"
    html += line(C + r"-\left(" + sp.latex(product) + r"\right)>0")
    html += line(sp.latex(sp.expand(a.numerator - a.left * a.denominator)) + ">0")
    html += system(
        [sp.latex(sp.factor(a.stage.original)) + ">0", choices("x", a.domain)]
    )
    html += (
        "<p>Решим неравенство методом интервалов и учтём ограничения. На рисунке показано их пересечение:</p>"
        + image
    )
    html += line(choices("x", a.solution))
    html += "<p>Примечание. Напомним, что</p>"
    html += line(r"\sqrt{u}>\sqrt{v}\iff\begin{cases}v\ge0\\u>v\end{cases}")
    html += "<p>При этом условие неотрицательности левого подкоренного выражения избыточно: величина, большая неотрицательной, заведомо положительна. Поэтому в нашем случае нет необходимости дополнительно решать неравенство</p>"
    html += line(C + r"\ge0")
    return html


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed three-root parent is required"
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
