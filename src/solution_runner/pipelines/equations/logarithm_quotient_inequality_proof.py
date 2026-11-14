"""Keep the parent's quotient, positive-factor reduction and three-row intersection."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .rational_inequality import FLIPPED
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION, interval_proof


def fraction_text(stage, *, factored=False):
    n, d = sp.fraction(sp.cancel(stage.original))
    if factored:
        n = real_factor(n, stage.zeros)
    return fraction(n, sp.factor(d))


def system(a, last, *, factored=False):
    rows = [
        (sp.latex(sp.factor(a.arguments[i])) if factored else a.argument_texts[i])
        + ">0"
        for i in a.displayed_indices
    ]
    rows.extend("x" + r"\ne " + sp.latex(p) for p in a.argument_holes)
    return line(r"\begin{cases}" + r"\\".join([*rows, last]) + r"\end{cases}")


def render(a, image, scope):
    if scope not in ("full_denominator", "positive_factor_removed"):
        raise UnsupportedCondition(
            "the figure must identify its displayed rational inequality"
        )
    A, B, C = a.arguments
    relation = RELATION[a.operator if a.base > 1 else FLIPPED[a.operator]]
    html = "<p>Решим неравенство, перейдя к равносильной системе. Разность логарифмов заменим логарифмом отношения на исходной области определения:</p>"
    html += system(
        a, r"\frac{" + sp.latex(A) + "}{" + sp.latex(B) + "}" + relation + sp.latex(C)
    )
    html += (
        "<p>Основание "
        + ("больше" if a.base > 1 else "меньше")
        + " единицы, поэтому при сравнении аргументов знак "
        + ("сохраняется" if a.base > 1 else "меняется")
        + ". Приведём разность дробей к общему знаменателю:</p>"
    )
    html += system(
        a, fraction_text(a.full_stage) + RELATION[a.operator] + "0", factored=True
    )
    html += system(
        a,
        fraction_text(a.full_stage, factored=True) + RELATION[a.operator] + "0",
        factored=True,
    )
    if scope == "full_denominator":
        html += (
            "<p>На схеме пересекаем условия положительности аргументов и полученное рациональное неравенство:</p>"
            + image
        )
    if sp.cancel(a.full_stage.original * B - a.stage.original) != 0:
        raise UnsupportedCondition(
            "removing the displayed positive factor must be an exact identity"
        )
    html += "<p>Средний аргумент положителен на рассматриваемой области. Поэтому умножение на него не меняет знак неравенства:</p>"
    html += line(sp.latex(B) + ">0")
    html += system(
        a,
        fraction_text(a.stage, factored=True) + RELATION[a.operator] + "0",
        factored=True,
    )
    html += interval_proof(a.stage, "")
    if scope == "positive_factor_removed":
        html += (
            "<p>Пересечём решение дробного неравенства с условиями положительности аргументов:</p>"
            + image
        )
    html += line(alternatives("x", a.solution))
    if a.displayed_indices == (0, 1):
        html += "<p>Условий существования логарифмов слева достаточно: правый аргумент положителен в силу сравнения с положительной левой частью.</p>"
    return html
