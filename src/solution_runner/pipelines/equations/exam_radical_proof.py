"""Keep squaring, substitutions and the symmetric parent's three methods in order."""

import sympy as sp

from ..calculus.common import real_roots
from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline
from .exam_exponential import T, X
from .exam_exponential_proof import n, root_set, second_part
from .exam_radical import candidates
from .exam_rational_proof import roots_line
from .exam_scalar import compare


def sqrt(p):
    return r"\sqrt{" + sp.latex(p) + "}"


def checked_candidates(a):
    html = roots_line(a.candidates)
    for r in a.candidates:
        if a.method == "equal":
            value = sp.simplify(a.radicands[1].subs(X, r))
            label = sp.latex(a.radicands[1])
        else:
            value = sp.simplify(a.right.subs(X, r))
            label = sp.latex(a.right)
        html += line(
            rf"\left.({label})\right|_{{x={n(r)}}}={n(value)}"
            + (r"\ge0" if compare(value, sp.Integer(0)) >= 0 else "<0")
        )
        html += (
            "<p>Это значение "
            + ("удовлетворяет" if r in a.selection.roots else "не удовлетворяет")
            + " условиям исходного уравнения.</p>"
        )
    return html


def square_method(a):
    p = a.radicands[0]
    if a.method == "equal":
        q = a.radicands[1]
        html = "<p>Подкоренные выражения должны быть равны и неотрицательны:</p>"
        html += line(
            sqrt(p)
            + "="
            + sqrt(q)
            + r"\iff\begin{cases}"
            + sp.latex(p)
            + "="
            + sp.latex(q)
            + r"\\"
            + sp.latex(q)
            + r"\ge0\end{cases}"
        )
        if all(
            coefficient >= 0 and power[0] % 2 == 0
            for power, coefficient in sp.Poly(q, X).terms()
        ):
            html += line(sp.latex(q) + r"\ge0\quad(x\in\mathbb R)")
    else:
        scaled = sp.expand(a.multiplier * a.right)
        root = (n(a.multiplier) if a.multiplier != 1 else "") + sqrt(p)
        html = "<p>Запишем исходное уравнение в виде:</p>" + line(
            root + "=" + sp.latex(scaled)
        )
        html += "<p>При отрицательной правой части корней нет. При неотрицательной правой части возведение в квадрат равносильно:</p>"
        html += line(
            r"\begin{cases}"
            + sp.latex(scaled)
            + r"\ge0\\"
            + sp.latex(a.multiplier**2 * p)
            + "=("
            + sp.latex(scaled)
            + r")^2\end{cases}"
        )
        html += line(
            sp.latex(sp.expand(scaled**2))
            + "="
            + sp.latex(sp.expand(a.multiplier**2 * p))
        )
    equation = (
        a.equation
        if a.method == "equal"
        else sp.expand(-(a.multiplier**2) * a.equation)
    )
    html += line(sp.latex(equation) + "=0")
    polynomial = sp.Poly(equation, X)
    if a.method == "equal" and set(polynomial.monoms()) == {(3,), (0,)}:
        html += line("x^3=" + sp.latex(-polynomial.nth(0) / polynomial.nth(3)))
        html += "<p>Кубическая функция строго возрастает, поэтому получаем единственный действительный корень:</p>"
    else:
        html += line(sp.latex(sp.factor(equation)) + "=0")
    return html + checked_candidates(a)


def substitution(a):
    p = a.radicands[0]
    slope, constant = sp.Poly(p, X).nth(1), sp.Poly(p, X).nth(0)
    back = (T * T - constant) / slope
    equation = sp.expand(a.multiplier * (a.right.subs(X, back) - T))
    levels = tuple(real_roots(equation, T))
    if any(not r.is_real for r in levels):
        raise UnsupportedCondition(
            "the alternative substitution needs real exact levels"
        )
    found = tuple(
        sp.simplify(back.subs(T, r)) for r in levels if compare(r, sp.Integer(0)) >= 0
    )
    if set(found) != set(a.selection.roots):
        raise UnsupportedCondition(
            "the alternative substitution must reproduce the original roots"
        )
    html = "<p>Примечание.</p>" + line(
        r"\sqrt{f(x)}=g(x)\iff\begin{cases}f(x)=g(x)^2\\g(x)\ge0\end{cases}"
    )
    html += "<p><b>Приведём другое решение пункта а):</b></p>"
    html += line("t=" + sqrt(p) + r"\ge0")
    html += line("x=" + sp.latex(back))
    html += line(
        sp.latex(a.multiplier * a.right.subs(X, back))
        + "="
        + sp.latex(a.multiplier * T)
    )
    html += line(sp.latex(equation) + "=0")
    html += line(sp.latex(sp.factor(equation)) + "=0")
    for r in levels:
        html += line("t=" + n(r))
        if compare(r, sp.Integer(0)) < 0:
            html += "<p>Отрицательное значение t не подходит арифметическому квадратному корню.</p>"
        else:
            html += line(sqrt(p) + "=" + n(r))
            html += line(sp.latex(p) + "=" + n(r * r))
            html += line("x=" + n(sp.simplify(back.subs(T, r))))
    return html


def symmetric_branches(a, reverse=False):
    c = a.radicands[0].subs(X, 0)
    branches = (X, -X - 1) if not reverse else (-X - 1, X)
    html = ""
    for y in branches:
        p = sp.expand(X * X - c - y)
        html += line("y=" + sp.latex(y) + r",\quad " + sp.latex(p) + "=0")
        html += roots_line(candidates(p))
    return html + checked_candidates(a)


def symmetric_first(a):
    p = a.radicands[0]
    html = "<p>Уравнение имеет решения, только если правая часть неотрицательна:</p>"
    html += line(sp.latex(a.right) + r"\ge0")
    html += "<p>Положим " + inline("y=" + sqrt(p)) + " и запишем систему:</p>"
    html += line(
        r"\begin{cases}y^2="
        + sp.latex(p)
        + r"\\y="
        + sp.latex(a.right)
        + r"\end{cases}"
    )
    html += "<p>Заменим первое уравнение системы суммой первого и второго:</p>"
    html += line(r"y^2+y=x^2+x")
    html += line(r"y^2-x^2+y-x=0")
    html += line(r"(y-x)(y+x+1)=0")
    return html + symmetric_branches(a)


def symmetric_alternatives(a):
    p = a.radicands[0]
    c = p.subs(X, 0)
    html = "<p><b>Приведём другое решение пункта а):</b></p>"
    html += line(sqrt(p) + "+" + n(c) + "=x^2")
    html += line(sqrt(p) + "+" + n(c) + r"+x+\frac14=x^2+x+\frac14")
    html += line("(" + sqrt(p) + r"+\frac12)^2=(x+\frac12)^2")
    html += line("(" + sqrt(p) + "-x)(" + sqrt(p) + "+x+1)=0")
    html += "<p>В каждой ветви правая часть должна быть неотрицательна:</p>"
    for y in (X, -X - 1):
        html += line(
            sqrt(p)
            + "="
            + sp.latex(y)
            + r"\iff\begin{cases}"
            + sp.latex(p)
            + "=("
            + sp.latex(y)
            + r")^2\\"
            + sp.latex(y)
            + r"\ge0\end{cases}"
        )
    html += symmetric_branches(a)
    html += "<p><b>Приведём еще одно решение пункта а):</b></p>"
    html += line(
        r"\begin{cases}"
        + sp.latex(p)
        + "=("
        + sp.latex(a.right)
        + r")^2\\"
        + sp.latex(a.right)
        + r"\ge0\end{cases}"
    )
    html += (
        "<p>Решим полученное уравнение как квадратное относительно числа "
        + inline(n(c))
        + ":</p>"
    )
    html += line("(" + n(c) + r")^2-(2x^2+1)\cdot(" + n(c) + r")+x^4-x=0")
    html += line(r"D=(2x^2+1)^2-4(x^4-x)=(2x+1)^2")
    html += line(n(c) + r"=\frac{2x^2+1\pm|2x+1|}{2}")
    html += "<p>Совокупность двух значений не меняется, если заменить модуль на выражение под ним:</p>"
    html += line(n(c) + r"=x^2+x+1\quad\text{или}\quad" + n(c) + r"=x^2-x")
    html += line(sp.latex(a.right) + r"\ge0")
    return html + symmetric_branches(a, reverse=True)


def render(a):
    selection = a.selection
    rendered = {r: n(r) for r in selection.roots}
    first = symmetric_first(a) if a.method == "symmetric" else square_method(a)
    if r"\log_" in selection.interval:
        from .exam_log_selection import selection as logarithmic_selection

        second = logarithmic_selection(selection, rendered)
    else:
        second = second_part(selection, rendered)
    if a.method == "symmetric":
        second += symmetric_alternatives(a)
    elif a.alternative:
        second += substitution(a)
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
