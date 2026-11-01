"""Show reviewed log bounds and numerator identities in their original method."""

import re

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S
from .power_arithmetic import balanced, clean


def bound(a, log):
    from .exam_trigonometric_proof import formula

    data = a.log_product
    html = "<p>На области определения аргумент логарифма положителен. Оценим его наибольшее значение с учётом границ синуса и косинуса:</p>"
    html += line(r"-1\le\sin x\le1,\quad -1\le\cos x\le1")
    html += line(
        "0<" + formula(data.argument) + r"\le " + sp.latex(data.nonzero_bound) + "<1"
    )
    html += "<p>Аргумент не равен единице, поэтому логарифмический множитель не равен нулю. Разделим на него, сохраняя исходную ОДЗ:</p>"
    return html + line(log + r"\ne0")


def numerator_identities(a, value, branches):
    from .exam_trigonometric_proof import formula

    html = ""
    for text, expression in a.identities:
        expression_text = clean(text)
        inner = ""
        if expression_text.startswith(r"\cos("):
            inner, _ = balanced(expression_text, 4, "(", ")")
            while inner.startswith("("):
                unwrapped, end = balanced(inner, 0, "(", ")")
                if end != len(inner):
                    break
                inner = unwrapped
        match = re.fullmatch(r"x\+(.+)", inner)
        if match:
            theta = match[1]
            html += "<p>Преобразуем первый сомножитель по формуле косинуса суммы:</p>"
            html += line(
                text
                + r"=\cos x\cos\left("
                + theta
                + r"\right)-\sin x\sin\left("
                + theta
                + r"\right)"
            )
            html += line(text + "=" + formula(expression))
    variables = {b.variable for b in branches}
    if (
        len(variables) == 1
        and variables <= {S, C}
        and not any(b.angle_shift for b in branches)
    ):
        variable = next(iter(variables))
        other = C if variable == S else S
        if value.is_polynomial(S, C) and value.has(other):
            projected = sp.expand(sp.rem(value, S * S + C * C - 1, other))
            if not projected.has(other):
                html += "<p>Применим следствие из основного тригонометрического тождества:</p>"
                html += line(formula(other**2) + "=" + formula(1 - variable**2))
                html += line(formula(value) + "=0")
                html += line(formula(projected) + "=0")
    return html


def double_angle(a):
    from .exam_trigonometric_log_product import failed
    from .exam_trigonometric_proof import formula, pi

    multiple, offset = a.log_product.double_angle
    angle = sp.latex(multiple * sp.Symbol("x", real=True))
    sin, cos = r"\sin\left(" + angle + r"\right)", r"\cos\left(" + angle + r"\right)"
    html = "<p>Вынесем общий тригонометрический множитель числителя, сохраняя исходный угол:</p>"
    html += line(
        sin
        + r"\left("
        + cos
        + ("+" if offset > 0 else "")
        + sp.latex(offset)
        + r"\right)=0"
    )
    html += line("-1" + r"\le " + cos + r"\le1")
    if offset > 1:
        html += line(
            cos + "+" + sp.latex(offset) + r"\ge " + sp.latex(offset - 1) + ">0"
        )
    else:
        html += line(
            cos + "+(" + sp.latex(offset) + r")\le " + sp.latex(offset + 1) + "<0"
        )
    html += "<p>Вторая скобка не равна нулю, поэтому остаётся уравнение:</p>"
    html += line(
        sin
        + r"=0\quad\Longleftrightarrow\quad "
        + angle
        + r"=\pi k,\quad k\in\mathbb Z"
    )
    html += line(r"x=\frac{\pi k}{" + str(multiple) + r"},\quad k\in\mathbb Z")
    html += "<p>Проверим все серии исходной области определения за один период:</p>"
    for k in range(2 * int(multiple)):
        q = sp.Rational(k, multiple)
        rejection = failed(a, q)
        if rejection:
            expression, relation, result = rejection
            html += line(
                "x="
                + pi(q)
                + r"+2\pi k:\quad "
                + formula(expression)
                + "="
                + sp.latex(result)
            )
            html += (
                "<p>Исходное ограничение "
                + (
                    "положительности аргумента"
                    if relation == "positive"
                    else "ненулевого знаменателя"
                )
                + " нарушено; эту серию исключаем.</p>"
            )
        else:
            html += line("x=" + pi(q) + r"+2\pi k,\quad k\in\mathbb Z")
    return html


def branch_notation(a, b, log_case, html):
    from dataclasses import replace

    from .exam_trigonometric_log_product import case_failed
    from .exam_trigonometric_proof import series_lines
    from .exam_trigonometric_selection import equivalent_series, periodic
    from .exam_trigonometric_variants import root_notation

    residues = tuple(q for q in b.residues if case_failed(a, q, log_case) is None)
    if not residues:
        return html
    matches = [
        (item, name)
        for item, name in zip(
            a.series, a.family_parameters or (a.parameter,) * len(a.series), strict=True
        )
        if equivalent_series((item,), periodic(residues))
    ]
    if len(matches) != 1:
        return html
    (q, period), name = matches[0]
    wanted = series_lines(((q, period),))[0]
    for shift in range(-2, 3):
        old = series_lines(((q + shift * period, period),))[0]
        html = html.replace(
            old + r",\quad k\in\mathbb Z", wanted + r",\quad k\in\mathbb Z"
        )
    return root_notation(replace(a, parameter=name, family_parameters=()), (html,))[0]
