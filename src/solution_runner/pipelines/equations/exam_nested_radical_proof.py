"""Preserve absolute-value substitution followed by the parent's squaring method."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import X
from .exam_exponential_proof import n
from .exam_scalar import compare


def interval_text(bounds):
    if bounds is None:
        return r"\varnothing"
    lo, hi, lc, uc = bounds
    if compare(lo, hi) == 0:
        return r"\{" + n(lo) + r"\}"
    return ("[" if lc else "(") + n(lo) + ";" + n(hi) + ("]" if uc else ")")


def first(a):
    k, c, h = a.coefficient, a.centre, a.coefficient / 2
    inner = sp.latex(X - c)
    html = "<p>а) Сделаем замену переменной:</p>" + line(r"y=\sqrt{" + inner + r"}\ge0")
    html += line(r"y^2=" + inner + r",\quad x=y^2+" + n(c))
    html += "<p>Оба подкоренных выражения становятся полными квадратами:</p>"
    html += line(
        r"\sqrt{y^2+"
        + n(k)
        + "y+"
        + n(c)
        + r"}+\sqrt{y^2-"
        + n(k)
        + "y+"
        + n(c)
        + "}="
        + n(k)
    )
    html += line(r"\sqrt{(y+" + n(h) + r")^2}+\sqrt{(y-" + n(h) + r")^2}=" + n(k))
    html += line(r"|y+" + n(h) + r"|+|y-" + n(h) + r"|=" + n(k))
    html += "<p>Так как y неотрицателен, первый модуль раскрывается со знаком плюс:</p>"
    html += line("y+" + n(h) + r"+|y-" + n(h) + "|=" + n(k))
    html += line(r"|y-" + n(h) + "|=" + n(h) + "-y")
    html += "<p>Равенство модуля выражения и противоположного ему числа верно только для неположительных значений выражения:</p>"
    html += line("0" + r"\le y\le" + n(h))
    html += line("0" + r"\le " + inner + r"\le " + n(c))
    return html + line(n(c) + r"\le x\le" + n(2 * c))


def second(a):
    c = a.centre
    if a.points:
        html = "<p>б) Проверим каждое из указанных чисел на принадлежность найденному отрезку:</p>"
        for t, accepted in zip(a.points, a.membership):
            if compare(t, c) < 0:
                formula = n(t) + "<" + n(c)
            elif compare(t, 2 * c) > 0:
                formula = n(2 * c) + "<" + n(t)
            else:
                formula = n(c) + r"\le" + n(t) + r"\le" + n(2 * c)
            html += line(formula)
            html += (
                "<p>Число "
                + inline(n(t))
                + (" является" if accepted else " не является")
                + " решением исходного уравнения.</p>"
            )
        return html
    html = "<p>б) Пересечём множество всех решений с заданным промежутком:</p>"
    for endpoint in a.bounds[:2]:
        for boundary in (c, 2 * c):
            order = compare(endpoint, boundary)
            html += line(
                n(endpoint)
                + ("<" if order < 0 else ">" if order > 0 else "=")
                + n(boundary)
            )
    html += line(
        "["
        + n(c)
        + ";"
        + n(2 * c)
        + r"]\cap"
        + a.interval
        + "="
        + interval_text(a.selected)
    )
    return html


def alternative(a):
    k, c = a.coefficient, a.centre
    inner = sp.latex(X - c)
    plus = r"\sqrt{x+" + n(k) + r"\sqrt{" + inner + "}}"
    minus = r"\sqrt{x-" + n(k) + r"\sqrt{" + inner + "}}"
    html = (
        "<p>При x ≥ "
        + inline(n(c))
        + " подкоренные выражения являются квадратами, как показано выше. Обе части исходного уравнения неотрицательны, поэтому возведём их в квадрат:</p>"
    )
    html += line(
        "x+"
        + n(k)
        + r"\sqrt{"
        + inner
        + "}+2"
        + plus
        + minus
        + "+x-"
        + n(k)
        + r"\sqrt{"
        + inner
        + "}="
        + n(k * k)
    )
    html += line(plus + minus + "=" + n(2 * c) + "-x")
    html += "<p>Произведение корней неотрицательно, поэтому при повторном возведении в квадрат сохраняем ограничение на правую часть:</p>"
    html += line(
        r"\begin{cases}x^2-"
        + n(k * k)
        + "("
        + inner
        + ")=("
        + n(2 * c)
        + r"-x)^2\\"
        + n(c)
        + r"\le x\le"
        + n(2 * c)
        + r"\end{cases}"
    )
    identity = sp.expand(X * X - k * k * (X - c))
    html += line(sp.latex(identity) + "=" + sp.latex(sp.expand((2 * c - X) ** 2)))
    html += "<p>Равенство выполняется тождественно. Оба возведения в квадрат равносильны при сохранённых ограничениях, следовательно, решением является отрезок:</p>"
    return html + line("[" + n(c) + ";" + n(2 * c) + "]")


def render(a):
    all_roots = "[" + n(a.centre) + ";" + n(2 * a.centre) + "]"
    if a.points:
        chosen = r";\ ".join(
            n(t) + r"\text{ — " + ("да" if yes else "нет") + "}"
            for t, yes in zip(a.points, a.membership)
        )
    else:
        chosen = interval_text(a.selected)
    html = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        + first(a)
        + second(a)
        + "</section>"
    )
    html += (
        '<section data-content-kind="solution" data-solution-title="Приведем другое решение.">'
        + alternative(a)
        + "</section>"
    )
    answer = "а) " + all_roots + "; б) " + chosen
    return (
        answer,
        "<p>а) " + inline(all_roots) + "; б) " + inline(chosen) + ".</p>",
        html,
    )
