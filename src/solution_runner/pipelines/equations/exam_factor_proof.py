"""Preserve direct factorization and the parent's alternative substitution note."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import T
from .exam_exponential_proof import back_substitution, labels, n, root_set, second_part
from .exam_scalar import compare


def power(a):
    base = sp.latex(a.base)
    if a.base.q != 1:
        base = r"\left(" + base + r"\right)"
    return base + "^{" + sp.latex(a.exponent) + "}"


def substitute(expression, variable):
    return sp.latex(expression.subs(T, sp.Symbol("Z"))).replace(
        "Z", "(" + variable + ")"
    )


def positive_roots(a, variable):
    html = line(
        (variable + "=") + (r",\quad " + variable + "=").join(n(t) for t in a.t_roots)
    )
    if any(compare(t, sp.Integer(0)) <= 0 for t in a.t_roots):
        html += "<p>Неположительные правые части не подходят, поскольку показательная функция строго положительна.</p>"
    return html


def first_part(result, rendered):
    a = result.equation
    variable = power(a)
    html = ""
    if result.algebraic is not None:
        html += "<p>Произведение равно нулю, когда хотя бы один из множителей равен нулю. Сначала решим алгебраическое уравнение:</p>"
        html += line(sp.latex(result.algebraic) + "=0")
        html += line(
            "x=" + r",\quad x=".join(rendered[r] for r in result.algebraic_roots)
        )
        html += "<p>Теперь приравняем нулю показательный множитель:</p>"
    if a.divisor:
        base, exponent = a.divisor
        html += "<p>Разделим обе части на положительное при любом действительном x выражение и приведём степени к одному основанию:</p>"
        html += line(sp.latex(base) + "^{" + sp.latex(exponent) + "}>0")
    else:
        html += "<p>Приведём степени к одному основанию и вынесем общую показательную часть, где это возможно:</p>"
    html += line(variable + ">0")
    html += line(substitute(result.normalized, variable) + "=0")
    if result.normalized != result.transformed:
        html += "<p>Умножим уравнение на общий знаменатель коэффициентов и сократим их общий множитель:</p>"
        html += line(substitute(result.transformed, variable) + "=0")
    if sp.Poly(result.transformed, T).degree() > 1:
        html += "<p>Разложим левую часть на множители:</p>"
        html += line(substitute(result.factored, variable) + "=0")
    html += positive_roots(a, variable)
    return html + back_substitution(a, rendered)


def alternative(result, rendered):
    a = result.equation
    html = "<p><b>Примечание.</b></p><p>Можно было ввести замену переменной, получить уравнение и решить его разложением на множители:</p>"
    html += line("t=" + power(a) + ">0")
    html += line(sp.latex(result.transformed) + "=0")
    html += line(sp.latex(result.factored) + "=0")
    html += positive_roots(a, "t")
    return html + back_substitution(replace(a, explicit=True), rendered)


def render(result):
    a = result.equation
    rendered = labels(a)
    rendered.update({r: n(r) for r in result.algebraic_roots})
    first = first_part(result, rendered)
    if r"\log_" in a.interval:
        from .exam_log_selection import selection

        second = selection(a, rendered)
    else:
        second = second_part(a, rendered)
    if result.alternate:
        second += alternative(result, rendered)
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    all_roots, selected = root_set(a.roots, rendered), root_set(a.selected, rendered)
    answer_html = "<p>а) " + inline(all_roots) + "; б) " + inline(selected) + ".</p>"
    return "а) " + all_roots + "; б) " + selected, answer_html, html
