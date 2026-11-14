"""Keep both numbered systems and their figures in the parent's order."""

import sympy as sp

from ..probability.common import line
from .exponential_inequality_preimage_proof import alternatives
from .logarithm_product_cancellation_proof import logarithm
from .rational_inequality_proof import RELATION


def system(rows):
    return line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")


def restrictions(a):
    affine = sp.factor(a.arguments[1].value / a.arguments[1].coefficient)
    return [sp.latex(affine) + ">0", r"x\ne" + sp.latex(a.hole)]


def signs(a, branch, *, logarithms=False, squares=False):
    pairs = (
        (a.ratio_root, branch.difference_stage),
        (a.product_root, branch.sum_stage),
    )
    rows = restrictions(a)
    for root, stage in pairs:
        value = sp.Pow(sp.factor(root), 2, evaluate=False)
        if logarithms:
            rows.append(
                logarithm(a.base, sp.latex(value)) + RELATION[stage.operator] + "0"
            )
        elif squares:
            rows.append(sp.latex(value) + RELATION[stage.operator] + "1")
        else:
            rows.append(
                sp.latex(sp.factor(stage.original)) + RELATION[stage.operator] + "0"
            )
    return rows


def render(a, images):
    A, B = (sp.factor(arg.value) for arg in a.arguments)
    log_A, log_B = (logarithm(a.base, sp.latex(value)) for value in (A, B))
    html = ""
    if a.atoms[0].base != a.atoms[1].base:
        html += "<p>Основания взаимно обратны. Соответствующие логарифмы противоположны, поэтому их квадраты равны:</p>"
        old = logarithm(a.atoms[1].base, a.arguments[1].raw)
        html += line(
            r"\left("
            + old
            + r"\right)^2=\left(-"
            + log_B
            + r"\right)^2=\left("
            + log_B
            + r"\right)^2"
        )
    html += "<p>Запишем разность квадратов и воспользуемся формулами суммы и разности логарифмов на исходной области определения:</p>"
    html += line(
        r"\left("
        + log_A
        + r"\right)^2-\left("
        + log_B
        + r"\right)^2"
        + RELATION[a.operator]
        + "0"
    )
    html += system(restrictions(a))
    html += line(
        r"\left("
        + log_A
        + "+"
        + log_B
        + r"\right)\left("
        + log_A
        + "-"
        + log_B
        + r"\right)"
        + RELATION[a.operator]
        + "0"
    )
    html += line(
        logarithm(a.base, sp.latex(sp.factor(A * B)))
        + r"\cdot"
        + logarithm(a.base, sp.latex(sp.factor(A / B)))
        + RELATION[a.operator]
        + "0"
    )
    html += "<p>Основание больше единицы. Получаем совокупность двух систем:</p>"
    html += system(signs(a, a.systems[0], logarithms=True)) + system(
        signs(a, a.systems[1], logarithms=True)
    )
    for index, branch in enumerate(a.systems):
        html += (
            "<p>"
            + (
                "Решим систему (1) равносильными преобразованиями:"
                if index == 0
                else "Аналогично преобразуем систему (2):"
            )
            + "</p>"
        )
        html += images[index]
        html += system(signs(a, branch, squares=True))
        if index == 0 and a.positive_factors:
            html += "<p>При разложении разности квадратов квадратный множитель положителен и не влияет на знак:</p>"
            for factor, completed in a.positive_factors:
                html += line(sp.latex(factor) + "=" + sp.latex(completed) + ">0")
        html += system(signs(a, branch))
        html += (
            line(alternatives("x", branch.solution))
            if branch.solution != sp.EmptySet
            else "<p>Эта система не имеет решений.</p>"
        )
    if all(branch.solution != sp.EmptySet for branch in a.systems):
        html += "<p>Объединим решения двух систем:</p>" + line(
            alternatives("x", a.solution)
        )
    return html.replace(r"\log_{10}", r"\lg") if a.base == 10 else html
