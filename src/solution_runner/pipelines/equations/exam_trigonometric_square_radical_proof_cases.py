"""Render the reviewed parent variants without replacing them by faster methods."""

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S


def proof(a):
    from .exam_trigonometric_proof import candidate_lines, families
    from .exam_trigonometric_square_radicals_proof import introduction
    from .exam_trigonometric_variants import argument

    data = a.square_radicals
    theta = argument(a.scale)
    html = introduction(a)
    if data.method == "absolute_level":
        html += absolute_level(data, theta)
    elif data.method == "remaining_absolute":
        html += remaining_absolute(data, theta)
    else:
        html += linear_absolute(a, theta)
    if data.method != "linear_absolute":
        for branch in a.branches:
            html += candidate_lines(
                branch, angle=theta, root_scale=a.scale, allow_inverse=a.allow_inverse
            )
    if a.merged or a.series_aligned or data.method == "linear_absolute":
        html += "<p>Объединим допустимые корни и, учитывая периодичность, запишем те же серии с целыми индексами:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return (
        "<p>Преобразуем корни в модули и рассмотрим допустимые ветви:</p>",
        html,
    )


def absolute_level(data, theta):
    t = sp.Symbol("t", real=True)
    polynomial = data.cases[0].subs(S, t)
    html = "<p>Пусть t — модуль синуса. Квадрат синуса равен квадрату его модуля, поэтому получаем квадратное уравнение при t ≥ 0:</p>"
    html += line(r"t=\left|\sin(" + theta + r")\right|,\quad0\le t\le1")
    html += line(sp.latex(polynomial) + "=0")
    if sp.Poly(polynomial, t).LC() < 0:
        factor = -data.remainder.subs(S, 0)
        if factor == 0:
            factor = -sp.S.One
        _, normalized = sp.expand(polynomial * factor).as_content_primitive()
        html += line(sp.latex(normalized) + "=0")
    for level in data.candidates[0]:
        html += line("t=" + sp.latex(level))
        if level not in data.accepted:
            html += "<p>Это значение не принадлежит отрезку [0;1], поэтому не может быть модулем синуса.</p>"
    html += "<p>Вернёмся к исходной переменной. Ненулевому модулю отвечают оба знака синуса, а нулевому — нулевой синус:</p>"
    for level in data.accepted:
        html += line(r"\left|\sin(" + theta + r")\right|=" + sp.latex(level))
        html += line(
            r"\sin(" + theta + (r")=\pm " if level else ")=") + sp.latex(level)
        )
    return html


def remaining_absolute(data, theta):
    from .exam_trigonometric_proof import formula

    show = lambda value: formula(value, theta)
    first, second = data.linears
    sign = data.signs[0]
    right = sp.expand(
        -(data.remainder + data.coefficients[0] * sign * first) / data.coefficients[1]
    )
    html = "<p>Первый модуль раскроем по его постоянному знаку на диапазоне синуса. Для второго сохраним обе ветви равенства модулю:</p>"
    html += line(show(first) + (r"\ge0" if sign > 0 else r"\le0"))
    html += line(r"\left|" + show(first) + r"\right|=" + show(sign * first))
    html += line(r"\left|" + show(second) + r"\right|=" + show(right))
    html += line(show(right) + r"\ge0")
    for choice, polynomial, candidates in zip((1, -1), data.cases, data.candidates):
        html += line(show(second) + "=" + show(choice * right))
        html += line(show(polynomial) + "=0")
        for level in candidates:
            html += line(show(S) + "=" + sp.latex(level))
            if level not in data.accepted:
                html += (
                    "<p>Значение за пределами [−1;1] не может быть синусом; исключаем эту ветвь.</p>"
                    if not -1 <= level <= 1
                    else "<p>Это значение не удовлетворяет исходному равенству модулей и исключается.</p>"
                )
    return html


def linear_absolute(a, theta):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_proof import candidate_lines, formula, pi

    data = a.square_radicals
    show = lambda value: formula(value, theta)
    right = sp.expand(-data.remainder / data.coefficients[0])
    html = "<p>Равенство модулю равносильно двум линейным ветвям при неотрицательной правой части:</p>"
    html += line(r"\left|" + show(data.linears[0]) + r"\right|=" + show(right))
    html += line(show(right) + r"\ge0")
    for case in data.cases:
        html += line(show(case) + "=0")
        for branch in solve_branches(case, a.preferred, a.allow_inverse)[1]:
            html += candidate_lines(
                branch, angle=theta, root_scale=a.scale, allow_inverse=a.allow_inverse
            )
            for q in branch.residues:
                value = sp.simplify(
                    right.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})
                )
                kept = compare(value, sp.S.Zero) >= 0
                html += line(
                    "x="
                    + pi(q / a.scale)
                    + r"\quad\Longrightarrow\quad "
                    + sp.latex(value)
                    + (r"\ge0" if kept else "<0")
                )
                if not kept:
                    html += "<p>Правая часть отрицательна; эта серия не удовлетворяет исходному равенству с модулем.</p>"
    return html
