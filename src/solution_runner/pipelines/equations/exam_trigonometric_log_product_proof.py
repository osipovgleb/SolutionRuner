"""Show the parent's zero-factor cases before checking their original log domains."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_log_product import conditions, failed, ratio_factor


def logarithm(base, argument):
    from .exam_trigonometric_proof import formula

    return (
        r"\log_{"
        + sp.latex(base)
        + r"}\left("
        + formula(ratio_factor(argument))
        + r"\right)"
    )


def proof(a):
    from .exam_trigonometric_proof import families, formula, pi, polynomial
    from .exam_trigonometric_radical_product import factor_branches

    data = a.log_product
    html = line(a.original)
    html += "<p>Аргументы логарифмов должны быть положительны, а знаменатели — отличны от нуля. Сохраним исходную область определения:</p>"
    for expression, relation in conditions(a):
        html += line(
            formula(ratio_factor(expression))
            + (">0" if relation == "positive" else r"\ne0")
        )
    if data.divide != 1:
        html += "<p>По исходной области определения этот множитель не равен нулю, поэтому разделим обе части уравнения на него:</p>"
        html += line(formula(data.divide) + r"\ne0")
    if data.denominator:
        html += line(
            logarithm(*data.denominator)
            + r"\ne0\quad\Longleftrightarrow\quad "
            + formula(data.denominator[1])
            + r"\ne1"
        )
        html += "<p>На исходной области определения знаменатель дроби не равен нулю. Поэтому дробь равна нулю тогда и только тогда, когда её числитель равен нулю:</p>"
    factor = ratio_factor(data.factor / data.divide)
    log = logarithm(data.base, data.argument)
    html += line(r"\left(" + formula(sp.factor(factor)) + r"\right)\cdot " + log + "=0")
    html += "<p>На области определения произведение равно нулю, если хотя бы один из его множителей равен нулю:</p>"
    for index, value in enumerate((factor, ratio_factor(data.argument - 1))):
        if index:
            html += "<p>Логарифм с допустимым постоянным основанием равен нулю тогда и только тогда, когда его аргумент равен единице:</p>"
            html += line(log + "=0")
            html += line(formula(ratio_factor(data.argument)) + "=1")
        else:
            html += "<p>Сначала приравняем нулю алгебраический множитель:</p>"
        for b in factor_branches(value, a.preferred, a.allow_inverse):
            if b.polynomial.subs(b.variable, 0) == 0 and 0 in b.candidates:
                b = replace(
                    b, candidates=(sp.S.Zero, *(v for v in b.candidates if v != 0))
                )
            html += polynomial(b, factorization=True, allow_inverse=a.allow_inverse)
            for q in b.residues:
                rejection = failed(a, q)
                if rejection is None:
                    continue
                expression, relation, result = rejection
                html += "<p>Проверим эту серию в исходной области определения; она не подходит:</p>"
                html += line(
                    "x="
                    + pi(q)
                    + r"+2\pi k:\quad "
                    + formula(ratio_factor(expression))
                    + "="
                    + sp.latex(result)
                )
                html += line(
                    formula(ratio_factor(expression))
                    + (r"\not>0" if relation == "positive" else "=0")
                )
    html += "<p>С учётом всех исходных ограничений остаются серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Решим уравнение, сохраняя область определения логарифмов:</p>", html
