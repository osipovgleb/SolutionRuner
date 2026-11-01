"""Keep the parent's complete-square, absolute-value and sine-range arguments."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import S


def proof(a):
    from .exam_trigonometric_proof import candidate_lines, families, formula
    from .exam_trigonometric_variants import argument

    data = a.square_radicals
    theta = argument(a.scale)
    show = lambda value: formula(value, theta)
    html = line(a.original)
    html += "<p>Выделим полные квадраты под корнями. Используем равенство √u² = |u| и диапазон синуса:</p>"
    html += line(r"-1\le " + show(S) + r"\le1")
    if r"\cos" in a.original:
        html += line(r"\cos(2(" + theta + r"))=1-2\sin^2(" + theta + ")")
        html += line(r"\cos^2(" + theta + r")=1-\sin^2(" + theta + ")")
    for radicand, linear in zip(data.radicands, data.linears):
        html += line(
            r"\sqrt{"
            + show(radicand)
            + r"}=\sqrt{("
            + show(linear)
            + r")^2}=\left|"
            + show(linear)
            + r"\right|"
        )
    absolute = data.remainder + sum(
        c * sp.Abs(v) for c, v in zip(data.coefficients, data.linears)
    )
    html += line(show(absolute) + "=0")
    if all(data.signs):
        html += "<p>На всём диапазоне синуса знаки выражений под модулями постоянны. Поэтому раскроем модули с учётом этих знаков:</p>"
        for linear, sign in zip(data.linears, data.signs):
            html += line(show(linear) + (r"\ge0" if sign > 0 else r"\le0"))
            html += line(r"\left|" + show(linear) + r"\right|=" + show(sign * linear))
        reduced = sp.expand(
            data.remainder
            + sum(
                c * s * v
                for c, s, v in zip(data.coefficients, data.signs, data.linears)
            )
        )
        html += line(show(reduced) + "=0")
        for level in data.candidates[0]:
            if level not in data.accepted:
                html += line(show(S) + "=" + sp.latex(level) + r"\notin[-1;1]")
    else:
        html += absolute_cases(data, theta)
        html += "<p>Вернёмся к исходной переменной:</p>"
    for branch in a.branches:
        html += candidate_lines(
            branch, angle=theta, root_scale=a.scale, allow_inverse=a.allow_inverse
        )
    if a.series_aligned:
        html += "<p>Сдвиг на целое число периодов меняет только нумерацию. Запишем те же корни в равносильной форме:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Преобразуем корни в модули, сохраняя ограничения:</p>", html


def absolute_cases(data, theta):
    t = sp.Symbol("t", real=True)
    right = sp.expand(-data.remainder / data.coefficients[0]).subs(S, t)
    linear = data.linears[0].subs(S, t)
    html = "<p>Сделаем замену тригонометрической функции переменной t. Равенство |u| = v равносильно двум ветвям u = v или u = −v при обязательном условии v ≥ 0:</p>"
    html += line(r"t=\sin(" + theta + r"),\quad -1\le t\le1")
    html += line(r"\left|" + sp.latex(linear) + r"\right|=" + sp.latex(right))
    html += line(sp.latex(right) + r"\ge0")
    html += line(
        r"\left[\begin{aligned}"
        + sp.latex(linear)
        + "&="
        + sp.latex(right)
        + r"\\"
        + sp.latex(linear)
        + "&=-("
        + sp.latex(right)
        + r")\end{aligned}\right."
    )
    for polynomial, levels in zip(data.cases, data.candidates):
        _, polynomial = polynomial.subs(S, t).as_content_primitive()
        html += line(sp.latex(sp.expand(polynomial)) + "=0")
        html += line(
            "t=" + r"\quad\text{или}\quad t=".join(sp.latex(v) for v in levels)
        )
    html += "<p>Проверим все полученные значения по диапазону синуса и неотрицательности правой части:</p>"
    for level in dict.fromkeys(v for row in data.candidates for v in row):
        if level in data.accepted:
            html += line(
                "t="
                + sp.latex(level)
                + r",\quad "
                + sp.latex(right.subs(t, level))
                + r"\ge0"
            )
        elif level < -1 or level > 1:
            html += line("t=" + sp.latex(level) + r"\notin[-1;1]")
        else:
            html += line(
                "t="
                + sp.latex(level)
                + r",\quad "
                + sp.latex(right.subs(t, level))
                + "<0"
            )
            html += "<p>Правая часть отрицательна, а модуль неотрицателен; это значение исключаем.</p>"
    return html
