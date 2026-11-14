"""Preserve the parent's two-fraction expansion, cancellation and sign normalization."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices, system
from .radical_inequality_comparison_proof import root
from .radical_inequality_even_figures import SOURCES, chart
from .radical_inequality_even_power import analyze
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION, normalized
from .rational_inequality_roots import real_roots


def render(a, image):
    _, _, d = a.first
    v, m, e = a.second
    initial = sp.Add(
        m,
        sp.Mul(v, e, evaluate=False),
        sp.Mul(a.radicand, e, evaluate=False),
        evaluate=False,
    )
    relation = RELATION[a.stage.operator] + "0"
    exclusions = [r"x\ne" + sp.latex(p) for p in a.constraints.excluded]
    html = "<p>Квадрат арифметического корня равен подкоренному выражению на исходной области определения:</p>"
    html += line(
        sp.latex(a.radicand)
        + r"\ge0\quad\Longrightarrow\quad\left("
        + root(a.radicand)
        + r"\right)^2="
        + sp.latex(a.radicand)
    )
    html += "<p>Исходные знаменатели должны быть ненулевыми. Поэтому данное неравенство эквивалентно системе:</p>"
    html += system(
        [
            sp.latex(a.radicand) + r"\ge0",
            *exclusions,
            fraction(a.first_numerator, d) + r"\cdot" + fraction(initial, e) + relation,
        ]
    )
    html += "<p>Разложим первый числитель на множители и раскроем скобки во втором:</p>"
    html += system(
        [
            choices("x", a.constraints.roots),
            fraction(sp.factor(a.first_numerator), d)
            + r"\cdot"
            + fraction(a.second_numerator, e)
            + relation,
            *exclusions,
        ]
    )
    html += "<p>Решим второе неравенство методом интервалов. Сокращаем общий множитель только при сохранённых исходных исключениях:</p>"
    cancelled = (
        fraction(a.cancelled_first, d)
        + r"\left("
        + sp.latex(a.second_numerator)
        + r"\right)"
        + relation
    )
    html += system([cancelled, *(r"x\ne" + sp.latex(p) for p in a.stage.holes)])
    html += "<p>Разложим квадратный трёхчлен на множители:</p>"
    second = real_factor(a.second_numerator, real_roots(a.second_numerator))
    html += line(
        fraction(a.cancelled_first, d)
        + r"\cdot\left("
        + sp.latex(second)
        + r"\right)"
        + relation
    )
    html += normalized(a.stage, already_factored=True)
    html += (
        "<p>Отметим на прямой нули выражения и все исходные запрещённые точки:</p>"
        + image
    )
    html += "<p>Учитывая исходное ограничение на подкоренное выражение, получаем:</p>"
    if a.solution != a.constraints.roots:
        html += line(choices("x", a.constraints.roots))
    return html + line(choices("x", a.solution))


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed even-root-power parent is required"
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
