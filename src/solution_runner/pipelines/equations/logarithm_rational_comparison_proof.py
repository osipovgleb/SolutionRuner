"""Preserve quotient reduction and the original positivity restrictions."""

import sympy as sp

from ..probability.common import line
from .exponential_inequality_preimage_proof import alternatives
from .rational_inequality import FLIPPED
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION


def domain(a):
    rows = [a.argument_texts[i] + ">0" for i in a.displayed_indices]
    rows += [r"x\ne" + sp.latex(p) for p in a.argument_holes]
    return line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}") + line(
        alternatives("x", a.domain)
    )


def fraction_text(stage, *, factored=False):
    n, d = sp.fraction(sp.cancel(stage.original))
    if factored:
        n, d = sp.factor(n), sp.factor(d)
    return sp.latex(n) if d == 1 else fraction(n, d)


def render(a, image="", *, method):
    A, B, C = a.arguments
    relation = RELATION[a.operator if a.base > 1 else FLIPPED[a.operator]]
    power = 2 if method == "power_quotient" else 1
    numerator = sp.Pow(A, power, evaluate=False) if power == 2 else A
    html = "<p>Определим область допустимых значений. Аргументы логарифмов должны быть положительны, а исходные знаменатели — отличны от нуля:</p>"
    if method == "power_quotient":
        html = "<p>Сначала учтём условия существования логарифмов слева и исходные знаменатели. Положительность правого аргумента проверим при сравнении:</p>"
    html += domain(a)
    html += "<p>Пользуясь свойствами степени и разности логарифмов, перейдём к логарифму отношения. При сравнении аргументов учитываем основание:</p>"
    html += line(
        r"\frac{"
        + sp.latex(numerator)
        + "}{"
        + sp.latex(B)
        + "}"
        + relation
        + sp.latex(C)
    )
    if method == "power_quotient":
        left = sp.cancel(A**2 / B)
        html += line(sp.latex(left) + relation + sp.latex(C))
        html += "<p>Левая часть положительна на найденной области. Поэтому неравенство обеспечивает положительность правого аргумента; отдельное условие для него уже выполнено.</p>"
        n, d = sp.fraction(sp.cancel(C - left))
        html += line(fraction_text(a.full_stage) + RELATION[a.stage.operator] + "0")
        html += "<p>Знаменатель положителен на исходной области. Умножим на него и разложим числитель на множители:</p>"
        html += line(sp.latex(d) + ">0")
        html += line(sp.latex(sp.expand(n)) + RELATION[a.stage.operator] + "0")
    else:
        html += (
            "<p>Приведём дроби к общему знаменателю и перенесём правую часть влево:</p>"
        )
        d = sp.fraction(sp.cancel(A / B - C))[1]
        html += line(
            fraction(sp.expand(sp.cancel(A / B * d)), d)
            + relation
            + fraction(sp.expand(sp.cancel(C * d)), d)
        )
        html += line(fraction_text(a.full_stage) + RELATION[a.operator] + "0")
        html += line(
            fraction_text(a.full_stage, factored=True) + RELATION[a.operator] + "0"
        )
        html += "<p>Средний аргумент положителен на исходной области, поэтому умножение на него сохраняет знак:</p>"
        html += line(sp.latex(B) + ">0")
    html += line(
        fraction_text(a.stage, factored=True) + RELATION[a.stage.operator] + "0"
    )
    html += "<p>Решим полученное неравенство методом интервалов и учтём исходную область определения:</p>"
    html += line(alternatives("x", a.stage.solution))
    return html + image + line(alternatives("x", a.solution))
