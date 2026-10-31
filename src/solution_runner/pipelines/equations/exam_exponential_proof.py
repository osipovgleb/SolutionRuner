"""Keep substitution, back-substitution and exact endpoint selection in two parts."""

from fractions import Fraction
from math import ceil, floor

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import number
from ..word_problems.water_season_proof import inline
from .exam_exponential import X, terms
from .exam_scalar import compare, enclose


def n(value):
    return number(value) if value.is_Rational else sp.latex(value)


def labels(a):
    result = {}
    for t, _, branch in a.back:
        for r in branch:
            if r.has(sp.log):
                p = sp.Poly(a.exponent, X)
                u, c = p.nth(1), p.nth(0)
                arg = sp.simplify(t * a.base ** (-c))
                text = r"\log_{" + sp.latex(a.base) + "}(" + n(arg) + ")"
                result[r] = text if u == 1 else r"\frac{" + text + "}{" + n(u) + "}"
            else:
                result[r] = n(r)
    return result


def root_set(roots, rendered):
    if not roots:
        return r"\varnothing"
    return r";\ ".join(rendered[r] for r in roots)


def fences(a, r):
    lower, upper, _, _ = a.bounds
    lo, hi = enclose(r)
    selected = r in a.selected
    for denominator in (1, 2, 3, 4, 5, 10, 20, 100):
        left = Fraction(floor(lo * denominator), denominator)
        right = Fraction(ceil(hi * denominator), denominator)
        if left == lo:
            left -= Fraction(1, denominator)
        if right == hi:
            right += Fraction(1, denominator)
        left, right = (sp.Rational(x.numerator, x.denominator) for x in (left, right))
        valid = (
            (compare(left, lower) >= 0 and compare(right, upper) <= 0)
            if selected
            else (compare(right, lower) <= 0 or compare(left, upper) >= 0)
        )
        if valid:
            return left, right
    raise UnsupportedCondition(
        "small exact root estimates must separate the requested interval"
    )


def preparation(a):
    A, B, _C = a.coefficients
    if a.divisor:
        from .exam_homogeneous import proof_prefix

        html = proof_prefix(a)
    else:
        html = "<p>Приведём степени к одному основанию, раскрывая постоянные сдвиги в показателях:</p>"
        powers, _ = terms(a.formula)
        for (coefficient, base, exponent), target, power in zip(powers, (A, B), (2, 1)):
            source = (
                (n(coefficient) + r"\cdot" if coefficient != 1 else "")
                + n(base)
                + "^{"
                + sp.latex(exponent)
                + "}"
            )
            replacement = (
                (n(target) + r"\cdot" if target != 1 else "")
                + "("
                + sp.latex(a.base)
                + "^{"
                + sp.latex(a.exponent)
                + "})"
                + ("^2" if power == 2 else "")
            )
            html += line(source + "=" + replacement)
    if a.explicit:
        html += "<p>Введём замену переменной. Показательная функция положительна при любом действительном x:</p>"
        html += line("t=" + sp.latex(a.base) + "^{" + sp.latex(a.exponent) + "}>0")
        html += "<p>Раскрывая постоянные сдвиги в показателях, получаем квадратное уравнение относительно t:</p>"
    else:
        html += "<p>Получаем квадратное уравнение относительно положительного показательного выражения:</p>"
    return html


def first_part(a, rendered):
    A, B, C = a.coefficients
    html = preparation(a)
    name = (
        "t"
        if a.explicit
        else "(" + sp.latex(a.base) + "^{" + sp.latex(a.exponent) + "})"
    )
    poly = A * sp.Symbol("t") ** 2 + B * sp.Symbol("t") + C
    html += line(
        (sp.latex(poly) if a.explicit else sp.latex(poly).replace("t", name)) + "=0"
    )
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
    html += (
        line((name + "=") + (r",\quad " + name + "=").join(n(t) for t in a.t_roots))
        if a.t_roots
        else "<p>Дискриминант отрицателен, действительных значений t нет.</p>"
    )
    if any(compare(t, sp.Integer(0)) <= 0 for t in a.t_roots):
        html += (
            "<p>Неположительные значения t не подходят, поскольку введённая показательная функция строго положительна.</p>"
            if a.explicit
            else "<p>Неположительные правые части не подходят, поскольку показательная функция строго положительна.</p>"
        )
    return html + back_substitution(a, rendered)


def back_substitution(a, rendered):
    html = ""
    for t, value, branch in a.back:
        html += (
            "<p>Вернёмся к исходной переменной при " + inline("t=" + n(t)) + ":</p>"
            if a.explicit
            else "<p>Решим уравнение с положительной правой частью:</p>"
        )
        html += line(sp.latex(a.base) + "^{" + sp.latex(a.exponent) + "}=" + n(t))
        html += line(
            sp.latex(a.exponent)
            + "="
            + (
                n(value)
                if value.is_Rational
                else r"\log_{" + sp.latex(a.base) + "}(" + n(t) + ")"
            )
        )
        if sp.Poly(a.exponent, X).degree() == 2:
            html += line(sp.latex(a.exponent - value) + "=0")
        html += (
            line("x=" + r",\quad x=".join(rendered[r] for r in branch))
            if branch
            else "<p>Эта ветвь не имеет действительных корней.</p>"
        )
    return html


def second_part(a, rendered):
    lower, upper, _lc, _uc = a.bounds
    html = (
        "<p>Отберём корни на промежутке "
        + inline(a.interval)
        + ". Для логарифмов используем монотонность показательной функции, а радикалы оцениваем сравнением квадратов неотрицательных чисел.</p>"
    )
    if lower.has(sp.pi) or upper.has(sp.pi):
        html += "<p>Для сравнения с границами используем оценки числа π:</p>"
        html += line(r"3<\pi<\frac{22}{7}")
    for r in a.roots:
        if compare(r, lower) == 0 or compare(r, upper) == 0:
            endpoint = lower if compare(r, lower) == 0 else upper
            html += line(rendered[r] + "=" + n(endpoint))
            html += (
                "<p>Корень совпадает с границей, которая "
                + ("включена" if r in a.selected else "не включена")
                + " в промежуток.</p>"
            )
            continue
        left, right = fences(a, r)
        if r.has(sp.log):
            p = sp.Poly(a.exponent, X)
            u, c = p.nth(1), p.nth(0)
            t = next(t for t, _, branch in a.back if r in branch)
            values = (a.base ** (u * left + c), t, a.base ** (u * right + c))
            sign = r"<" if (u > 0) == (a.base > 1) else r">"
            html += line(sign.join(n(v) for v in values))
        html += line(n(left) + "<" + rendered[r] + "<" + n(right))
        html += (
            "<p>Следовательно, этот корень "
            + ("принадлежит" if r in a.selected else "не принадлежит")
            + " заданному промежутку.</p>"
        )
    if not a.roots:
        html += "<p>Исходное уравнение не имеет действительных корней, поэтому отбирать нечего.</p>"
    return html


def render(a):
    rendered = labels(a)
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first_part(a, rendered)
        + '</li><li data-list-marker="б)">'
        + second_part(a, rendered)
        + "</li></ol>"
    )
    all_roots, selected = root_set(a.roots, rendered), root_set(a.selected, rendered)
    answer_html = "<p>а) " + inline(all_roots) + "; б) " + inline(selected) + ".</p>"
    return "а) " + all_roots + "; б) " + selected, answer_html, html
