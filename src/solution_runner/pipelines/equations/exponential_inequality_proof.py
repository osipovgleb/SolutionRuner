"""Retain common-base rewrites, increasing-function comparison and exact intervals."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_common_base import vector, weight
from .rational_inequality import set_latex
from .rational_inequality_proof import RELATION


def power(base, exponent):
    text = sp.latex(base)
    if base.is_Integer is not True:
        text = r"\left(" + text + r"\right)"
    return text + "^{" + sp.latex(exponent) + "}"


def rewrites(a):
    values = []
    for coefficient, base, _ in a.powers:
        for value in (coefficient, base):
            if value not in (1, a.base) and value not in values:
                values.append(value)
    if not values:
        return ""
    return (
        "<p>Представим основания и коэффициенты как степени одного основания:</p>"
        + line(
            r",\quad ".join(
                sp.latex(value) + "=" + power(a.base, weight(value, vector(a.base)))
                for value in values
            )
        )
    )


def render(a):
    left, right = a.exponents
    stage = a.stage
    html = "<p>Последовательно получаем:</p>" + line(a.formula) + rewrites(a)
    html += line(
        power(a.base, left) + RELATION[a.operator] + " " + power(a.base, right)
    )
    html += (
        "<p>Основание "
        + inline(sp.latex(a.base) + ">1")
        + "; показательная функция возрастает. Поэтому сравним показатели:</p>"
    )
    html += line(sp.latex(left) + RELATION[a.operator] + " " + sp.latex(right))
    html += "<p>Перенесём всё в левую часть и приведём подобные слагаемые:</p>"
    html += line(sp.latex(sp.expand(stage.original)) + RELATION[stage.operator] + "0")
    ratio = (
        sp.cancel(stage.original / stage.expression)
        if stage.expression != 0
        else sp.Integer(1)
    )
    if ratio != 1:
        adjective = "отрицательный" if ratio < 0 else "положительный"
        change = "меняется" if ratio < 0 else "сохраняется"
        html += (
            "<p>Делим обе части на "
            + adjective
            + " множитель "
            + inline(sp.latex(ratio))
            + ": знак неравенства "
            + change
            + ".</p>"
        )
        html += line(
            sp.latex(sp.expand(stage.expression)) + RELATION[stage.sign_operator] + "0"
        )
    html += "<p>Решим полученное неравенство методом интервалов:</p>"
    html += line(
        sp.latex(sp.factor(stage.expression)) + RELATION[stage.sign_operator] + "0"
    )
    return html + line(r"x\in " + set_latex(stage.solution))
