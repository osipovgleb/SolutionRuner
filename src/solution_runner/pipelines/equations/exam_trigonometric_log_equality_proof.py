"""Keep log definitions, matching exponentials, grouping and original positive arguments."""

from dataclasses import replace
from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C
from .exam_trigonometric_log_equality import order_branches
from .exam_trigonometric_log_method_proof import branch_notation, numerator_identities
from .exam_trigonometric_log_product_proof import branches_proof, rejections
from .exam_trigonometric_radical_product import factor_branches


def grouping(a, branch):
    from .exam_trigonometric_proof import candidate_lines, formula

    data = a.log_product
    values = tuple(
        sorted(
            branch.candidates,
            key=cmp_to_key(compare),
            reverse=data.level_ascending is False,
        )
    )
    if len(values) != 2 or sp.degree(branch.polynomial, branch.variable) != 2:
        return branches_proof(a, (branch,), False, factorization=True)
    first, second = values
    v = branch.variable
    common = sp.expand(sp.Poly(branch.polynomial, v).LC() * (v - second))
    html = "<p>Сгруппируем слагаемые, выделяя общий двучлен:</p>"
    html += line(
        formula(v)
        + r"\left("
        + formula(common)
        + r"\right)-("
        + sp.latex(first)
        + r")\left("
        + formula(common)
        + r"\right)=0"
    )
    html += line(
        r"\left("
        + formula(v)
        + "-("
        + sp.latex(first)
        + r")\right)\left("
        + formula(common)
        + r"\right)=0"
    )
    b = replace(branch, candidates=values)
    return html + branch_notation(
        a,
        b,
        False,
        candidate_lines(b, allow_inverse=a.allow_inverse) + rejections(a, b),
    )


def proof(a):
    from .exam_trigonometric_proof import families, formula

    data = a.log_product
    e = data.equality
    base = (
        sp.latex(data.base)
        if data.base.is_Integer
        else r"\left(" + sp.latex(data.base) + r"\right)"
    )
    html = line(a.original)
    html += "<p>Запишем уравнение по определению логарифма:</p>"
    if e.kind == "two_logs":
        html += line(e.argument_text + "=" + e.right_text)
        html += "<p>Сохраним положительность обоих исходных аргументов:</p>"
        html += line(formula(data.argument) + ">0") + line(
            formula(e.other_argument) + ">0"
        )
    else:
        target = sp.latex(data.base**e.target)
        html += line(
            e.argument_text
            + "="
            + base
            + "^{"
            + e.right_text
            + "}"
            + ("=" + target if e.kind == "constant" else "")
        )
        if e.kind == "exponential":
            html += line(e.power_text + "=" + base + "^{x}")
        html += "<p>Аргумент приравнен к положительному числу. Поэтому исходное условие его положительности выполнено для каждого решения полученного уравнения:</p>"
        html += line(base + "^{" + e.right_text + "}>0")
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    for text, value in a.identities:
        if text not in (r"\sin(x)", r"\cos(x)"):
            html += line(text + "=" + formula(value))
    html += line(formula(a.raw) + "=0")
    value = sp.cancel(data.factor / data.divide)
    if data.divide != 1:
        coefficient = sp.cancel(e.other_argument / C)
        html += line(
            r"\cos x"
            + (">0" if coefficient.is_positive else "<0")
            + r"\quad\Longrightarrow\quad\cos x\ne0"
        )
        html += "<p>На исходной области определения косинус не равен нулю, поэтому разделим на него:</p>"
        html += line(formula(value) + "=0")
    branches = order_branches(e, factor_branches(value, a.preferred, a.allow_inverse))
    html += numerator_identities(a, value, branches)
    prefix = html if e.image_after_reduction else ""
    if prefix:
        html = ""
    if len(branches) > 1:
        html += "<p>Вынесем общий тригонометрический множитель и приравняем множители нулю:</p>"
        html += line(formula(sp.factor(value, extension=True)) + "=0")
    for b in branches:
        html += (
            grouping(a, b)
            if e.grouping
            else branches_proof(a, (b,), False, factorization=False)
        )
    if e.centre_inverse:
        for b in branches:
            for v in b.values:
                if v.is_negative is True and sp.acos(v).has(sp.acos):
                    html += line(
                        r"\arccos\left("
                        + sp.latex(v)
                        + r"\right)=\pi-\arccos\left("
                        + sp.latex(-v)
                        + r"\right)"
                    )
    html += "<p>Получаем серии корней с учётом всех исходных ограничений:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return prefix or "<p>Преобразуем исходное логарифмическое уравнение:</p>", html
