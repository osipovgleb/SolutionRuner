"""Retain the sine, half-angle and geometric notes of an auxiliary-angle method."""

from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S


def split(parent_html):
    soup = BeautifulSoup(parent_html.replace("\xad", ""), "html.parser")
    headings = [
        p
        for p in soup.find_all("p")
        if p.get_text(strip=True).lower() in ("примечание 1.", "примечание 2.")
    ]
    if not headings:
        return parent_html, False
    text = soup.get_text(" ", strip=True).lower()
    if (
        len(headings) != 2
        or [h.get_text(strip=True).lower() for h in headings]
        != ["примечание 1.", "примечание 2."]
        or headings[0].parent is not headings[1].parent
        or len(soup.find_all("img")) != 2
        or "вспомогательного угла" not in text
        or "формулы двойных углов" not in text
        or "точки пересечения" not in text
    ):
        raise UnsupportedCondition(
            "the auxiliary-angle notes require all three reviewed methods and figures"
        )
    for node in list(headings[0].next_siblings):
        node.extract()
    headings[0].extract()
    return str(soup), True


def half_angle(a):
    from .exam_trigonometric import select, solve_branches
    from .exam_trigonometric_domain import without_poles
    from .exam_trigonometric_selection import equivalent_series, restricted_series

    alpha, beta = a.raw.coeff(S), a.raw.coeff(C)
    if (
        alpha not in (-1, 1)
        or beta not in (-1, 1)
        or a.raw != alpha * S + beta * C + beta
        or a.poles != (S,)
        or a.translation
        or a.scale.is_Integer is not True
        or a.scale % 2
        or not 2 <= a.scale <= 12
    ):
        raise UnsupportedCondition(
            "the reviewed auxiliary notes require equal-magnitude coefficients and an even base angle"
        )
    raw = 2 * C * (alpha * S + beta * C)
    _, branches = solve_branches(raw, C, True)
    branches = without_poles(branches, (2 * S * C,))
    series = tuple(
        (q / (a.scale / 2), p / (a.scale / 2))
        for b in branches
        for q, p in restricted_series(b)
    )
    if (
        not equivalent_series(series, a.series)
        or select(series, a.bounds)[0] != a.selected
    ):
        raise UnsupportedCondition(
            "the half-angle note must recover exactly the primary roots"
        )
    return raw, branches


def notes(a, system_image):
    from .exam_trigonometric_linear_phase import branch, proof
    from .exam_trigonometric_proof import formula, polynomial, series_lines
    from .exam_trigonometric_variants import argument

    raw, branches = half_angle(a)
    theta = argument(a.scale)
    sine = branch(a.raw)
    sine = replace(sine, residues=a.branches[0].residues)
    html = "<p><b>Примечание 1.</b></p><p>Мы воспользовались введением вспомогательного угла. Можно использовать формулу синуса суммы:</p>"
    html += proof(sine, theta, a.scale, sine.residues)
    half = argument(a.scale / 2)
    html += "<p>Третий путь — применить формулы двойных углов и свести уравнение к однородному:</p>"
    html += line(r"\sin(" + theta + r")=2\sin(" + half + r")\cos(" + half + ")")
    html += line(r"\cos(" + theta + r")=2\cos^2(" + half + ")-1")
    html += line(
        formula(a.raw, theta)
        + "="
        + formula(sp.expand(raw), half)
        + "="
        + formula(raw, half)
    )
    html += line(formula(2 * S * C, half) + r"\ne0")
    for b in branches:
        html += polynomial(
            b,
            angle=half,
            root_scale=a.scale / 2,
            allowed_residues=b.residues,
            allow_inverse=True,
        )
    html += (
        "<p>Оставлены только корни исходной области определения.</p><p><b>Примечание 2.</b></p>"
        + system_image
    )
    html += "<p>Ещё один способ решить систему — пересечь прямую с единичной окружностью. Красными крестами исключены точки, в которых исходный знаменатель равен нулю:</p>"
    html += line(formula(a.raw, theta) + "=0") + line(formula(S, theta) + r"\ne0")
    for text in series_lines(tuple((q * a.scale, p * a.scale) for q, p in a.series)):
        html += line(text.replace("x=", theta + "=", 1) + r",\quad k\in\mathbb Z")
    return html


def primary_proof(a):
    from .exam_trigonometric_linear_phase import proof
    from .exam_trigonometric_phase_domain import proof as exclusions
    from .exam_trigonometric_proof import formula
    from .exam_trigonometric_variants import argument

    theta = argument(a.scale)
    html = "<p>Запишем исходную область определения:</p>" + line(
        formula(S, theta) + r"\ne0"
    )
    html += line(a.original)
    html += "<p>Используем определение котангенса и формулу приведения:</p>"
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value, theta))
    html += "<p>Умножим на ненулевой знаменатель и введём вспомогательный угол:</p>"
    b = a.branches[0]
    html += proof(b, theta, a.scale, b.residues)
    html += exclusions(b, a.poles, scale=a.scale)
    return "<p>Преобразуем уравнение с учётом области определения:</p>", html
