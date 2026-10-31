"""Retain reciprocal substitution, equal-square branches and original domains."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import T, X
from .exam_exponential_proof import n, root_set, second_part
from .exam_rational_input import Y


def substitution_text(a):
    u = a.substitution.coeff(Y, 1)
    v = a.substitution.coeff(Y, -1)
    shift = sp.latex(X - a.pole)
    first = shift if u == 1 else r"\frac{" + shift + "}{" + n(1 / u) + "}"
    return first + r"-\frac{" + n(-v) + "}{" + shift + "}"


def roots_line(roots):
    return (
        line("x=" + r",\quad x=".join(n(r) for r in roots))
        if roots
        else "<p>Эта ветвь не имеет действительных корней.</p>"
    )


def domain(a):
    html = "<p>Сохраним ограничение исходного знаменателя:</p>"
    if a.denominator is not None:
        html += line(sp.latex(a.denominator) + r"\ne0")
    return html + line(r"x\ne" + n(a.pole))


def reciprocal(a):
    u = a.substitution.coeff(Y, 1)
    v = a.substitution.coeff(Y, -1)
    shift = X - a.pole
    text = substitution_text(a)
    html = domain(a) + "<p>Введём замену и возведём выражение в квадрат:</p>"
    html += line("t=" + text)
    square = u * u * shift**2 + 2 * u * v + v * v / shift**2
    html += line("t^2=" + sp.latex(square))
    html += "<p>Подставляя полученное тождество в исходное уравнение и собирая коэффициенты, получаем квадратное уравнение:</p>"
    original = sp.expand(a.original.subs(X, Y + a.pole))
    coefficient = original.coeff(Y, 2) / u**2
    converted = sp.Add(
        sp.Mul(coefficient, T * T - 2 * u * v, evaluate=False),
        original.coeff(Y, 1) / u * T,
        original.coeff(Y, 0),
        evaluate=False,
    )
    html += line(sp.latex(converted) + "=0")
    html += line(sp.latex(a.quadratic) + "=0")
    A, B, C = sp.Poly(a.quadratic, T).all_coeffs()
    html += line(
        "D=("
        + n(B)
        + r")^2-4\cdot"
        + n(A)
        + r"\cdot("
        + n(C)
        + ")="
        + n(B * B - 4 * A * C)
    )
    if a.branches:
        html += line("t=" + r",\quad t=".join(n(b.value) for b in a.branches))
    else:
        html += "<p>Квадратное уравнение не имеет действительных корней.</p>"
    for b in a.branches:
        html += (
            "<p>Вернёмся к исходной переменной при "
            + inline("t=" + n(b.value))
            + ". При сохранённом ограничении на знаменатель умножение на него равносильно:</p>"
        )
        html += line(text + "=" + n(b.value))
        html += line(sp.latex(u * shift**2 - b.value * shift + v) + "=0")
        html += line(sp.latex(b.polynomial) + "=0")
        html += roots_line(b.candidates)
    return html + rejected(a)


def equal_squares(a):
    P, Q = a.numerators
    html = (
        domain(a)
        + "<p>При ненулевом общем знаменателе отбросим знаменатели. Квадраты равны, если сами выражения равны либо противоположны:</p>"
    )
    html += line("(" + sp.latex(P) + ")^2=(" + sp.latex(Q) + ")^2")
    for b in a.branches:
        html += line(
            sp.latex(P) + "=" + ("" if b.value == 1 else "-") + "(" + sp.latex(Q) + ")"
        )
        html += line(sp.latex(b.polynomial) + "=0")
        html += roots_line(b.candidates)
    return html + rejected(a)


def rejected(a):
    excluded = tuple(
        dict.fromkeys(r for b in a.branches for r in b.candidates if r not in b.roots)
    )
    html = ""
    if excluded:
        html += "<p>Следующие кандидаты не удовлетворяют ограничению исходного знаменателя и отбрасываются:</p>"
        html += roots_line(excluded)
    else:
        html += "<p>Все найденные кандидаты удовлетворяют ограничению исходного знаменателя.</p>"
    return html


def render(a):
    selection = a.selection
    rendered = {r: n(r) for r in selection.roots}
    first = equal_squares(a) if a.substitution is None else reciprocal(a)
    if r"\log_" in selection.interval:
        from .exam_log_selection import selection as logarithmic_selection

        second = logarithmic_selection(selection, rendered)
    else:
        second = second_part(selection, rendered)
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    all_roots, chosen = (
        root_set(selection.roots, rendered),
        root_set(selection.selected, rendered),
    )
    answer_html = "<p>а) " + inline(all_roots) + "; б) " + inline(chosen) + ".</p>"
    return "а) " + all_roots + "; б) " + chosen, answer_html, html
