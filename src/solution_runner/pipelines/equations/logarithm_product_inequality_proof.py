"""Keep the parent's logarithm system, cubic grouping and domain intersection."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_reduction_proof import sum_terms
from .rational_exponential_figures import multiplicity
from .rational_inequality import FLIPPED
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION, interval_proof


def grouping(a):
    candidates = [
        r
        for r in a.stage.zeros
        if r.is_Rational is True and multiplicity(a.stage.original, r) == 1
    ]
    if len(candidates) != 1:
        raise UnsupportedCondition(
            "the source grouping needs one simple rational linear factor"
        )
    factor = X - candidates[0]
    q, remainder = sp.div(a.stage.original, factor, X)
    if remainder != 0 or polynomial(q).degree() != 2:
        raise UnsupportedCondition(
            "the displayed linear factor must divide the cubic exactly"
        )
    grouped = sum_terms(
        [
            (
                c,
                (sp.latex(X**k) if k else "")
                + r"\left("
                + sp.latex(factor)
                + r"\right)",
            )
            for (k,), c in polynomial(q).terms()
        ]
    )
    relation = RELATION[a.operator] + "0"
    html = line(sp.latex(a.stage.original) + relation)
    html += line(grouped + relation)
    return html + line(sp.latex(sp.factor(a.stage.original)) + relation)


def render(a):
    A, B, C = a.arguments
    op = a.operator if a.base > 1 else FLIPPED[a.operator]
    product = sp.Mul(B, C, evaluate=False)
    rows = [sp.latex(a.arguments[i]) + ">0" for i in a.displayed_indices]
    rows.append(sp.latex(A) + RELATION[op] + sp.latex(product))
    html = "<p>Пользуясь свойствами логарифма, объединим сумму справа в логарифм произведения и перейдём к равносильной системе:</p>"
    html += (
        "<p>Основание "
        + ("больше" if a.base > 1 else "меньше")
        + " единицы, поэтому знак сравнения аргументов "
        + ("сохраняется" if a.base > 1 else "меняется")
        + ".</p>"
    )
    html += line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")
    factored = [sp.latex(sp.factor(a.arguments[i])) + ">0" for i in a.displayed_indices]
    factored.append(sp.latex(a.stage.original) + RELATION[a.operator] + "0")
    html += line(r"\begin{cases}" + r"\\".join(factored) + r"\end{cases}")
    html += "<p>Решим условия положительности аргументов:</p>" + line(
        alternatives("x", a.display_domain)
    )
    html += "<p>Рассмотрим кубическое неравенство. Сгруппируем слагаемые и вынесем общий множитель:</p>"
    html += grouping(a)
    for factor, completed in positive_quadratics(a.stage):
        html += "<p>Квадратный множитель положителен при всех действительных x:</p>"
        left, right = sp.latex(factor), sp.latex(completed)
        html += line(left + ("=" + right if left != right else "") + ">0")
    if any(multiplicity(a.stage.original, r) > 1 for r in a.stage.zeros):
        html += "<p>Кратный нуль не меняет знак, но его принадлежность решению проверяем по исходному знаку неравенства; при строгом сравнении он исключён.</p>"
    html += interval_proof(a.stage, "")
    html += (
        "<p>Пересечём полученные промежутки с условиями существования логарифмов:</p>"
    )
    html += line(alternatives("x", a.solution))
    if len(a.displayed_indices) < 3:
        html += "<p>Оставшийся аргумент положителен в силу сравнения с положительным произведением, поэтому все исходные логарифмы определены.</p>"
    return html
