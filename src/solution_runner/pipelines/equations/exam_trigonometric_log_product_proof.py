"""Show the parent's zero-factor cases before checking their original log domains."""

from dataclasses import replace
from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_log_product import (
    case_failed,
    conditions,
    failed,
    ratio_factor,
    zero_cases,
)


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
    from .exam_trigonometric_proof import families, formula
    from .exam_trigonometric_radical_product import factor_branches

    data = a.log_product
    html = line(a.original)
    html += "<p>Аргументы логарифмов должны быть положительны, а знаменатели — отличны от нуля. Сохраним исходную область определения:</p>"
    domain = conditions(a)
    if data.domain_labels:
        domain = tuple(sorted(domain, key=lambda item: item[1] == "positive"))
    for expression, relation in domain:
        html += line(
            formula(ratio_factor(expression))
            + (">0" if relation == "positive" else r"\ne0")
            + (
                (r"\quad(**)" if relation == "positive" else r"\quad(*)")
                if data.domain_labels
                else ""
            )
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
    log = logarithm(data.base, data.argument) if data.argument is not None else ""
    from .exam_trigonometric_log_method_proof import (
        bound,
        double_angle,
        numerator_identities,
    )

    if data.nonzero_bound is not None:
        html += bound(a, log)
    if data.argument is not None and data.nonzero_bound is None:
        html += line(
            r"\left(" + formula(sp.factor(factor)) + r"\right)\cdot " + log + "=0"
        )
        html += "<p>На области определения произведение равно нулю, если хотя бы один из его множителей равен нулю:</p>"
    if data.double_angle is not None:
        html += double_angle(a)
    for log_case, value in () if data.double_angle else zero_cases(data):
        if log_case:
            html += "<p>Логарифм с допустимым постоянным основанием равен нулю тогда и только тогда, когда его аргумент равен единице:</p>"
            html += line(log + "=0")
            html += line(formula(ratio_factor(data.argument)) + "=1")
        else:
            html += (
                "<p>Сначала приравняем нулю алгебраический множитель:</p>"
                if not data.log_first
                else "<p>Теперь рассмотрим случай ненулевого логарифма и решим уравнение для алгебраического множителя:</p>"
            )
            if data.log_first:
                html += line(log + r"\ne0")
        case_branches = factor_branches(value, a.preferred, a.allow_inverse)
        if not log_case:
            html += numerator_identities(a, value, case_branches)
        html += branches_proof(a, case_branches, log_case)
    html += "<p>С учётом всех исходных ограничений остаются серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Решим уравнение, сохраняя область определения логарифмов:</p>", html


def branches_proof(a, case_branches, log_case):
    from .exam_trigonometric_log_method_proof import branch_notation
    from .exam_trigonometric_proof import polynomial

    data = a.log_product
    html = ""
    for b in case_branches:
        if data.level_ascending is not None:
            from .exam_scalar import compare

            b = replace(
                b,
                candidates=tuple(
                    sorted(
                        b.candidates,
                        key=cmp_to_key(compare),
                        reverse=not data.level_ascending,
                    )
                ),
            )
        elif b.polynomial.subs(b.variable, 0) == 0 and 0 in b.candidates:
            b = replace(b, candidates=(sp.S.Zero, *(v for v in b.candidates if v != 0)))
        branch_html = polynomial(b, factorization=True, allow_inverse=a.allow_inverse)
        branch_html += rejections(a, b, log_case)
        html += branch_notation(a, b, log_case, branch_html)
    return html


def rejections(a, b, log_case=False):
    from .exam_trigonometric_proof import formula, pi

    html = ""
    for q in b.residues:
        rejection = case_failed(a, q, log_case)
        if rejection is None:
            continue
        expression, relation, result = rejection
        if failed(a, q) is None:
            html += "<p>Эта серия уже получена в случае нулевого логарифма. В текущем случае логарифм должен быть ненулевым, поэтому здесь серию исключаем:</p>"
        else:
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
    return html
