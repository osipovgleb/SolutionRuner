"""Keep the parent's signed alternatives, chart, factors and final union."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_inequality import analyze
from .absolute_inequality_proof import alternative_rows
from .absolute_quadratic_figures import SOURCES, chart
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .rational_inequality_figures import read_formula


def render(a, image):
    html = "<p>Неравенство равносильно совокупности двух неравенств:</p>"
    html += alternative_rows(
        [
            sp.latex(a.argument) + r"\ge " + sp.latex(a.bound),
            sp.latex(-a.argument) + r"\ge " + sp.latex(a.bound),
        ]
    )
    html += "<p>Перенесём всё влево. Разделив каждую строку на положительный старший коэффициент, получаем:</p>"
    html += alternative_rows([sp.latex(s.original) + r"\le0" for s in a.branches])
    html += image
    html += (
        "<p>Разложим квадратные трёхчлены на множители и решим каждое неравенство:</p>"
    )
    html += alternative_rows(
        [sp.latex(sp.factor(s.original)) + r"\le0" for s in a.branches]
    )
    html += alternative_rows([alternatives("x", s.solution) for s in a.branches])
    return (
        html
        + "<p>Объединяя полученные промежутки, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed quadratic-modulus parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula, "quadratic_comparison")
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
