"""Keep positive division, both factor branches and the parent's explanation order."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_power_grouping import X, Y

THETA = sp.Symbol("theta", real=True)


def expression(value, data):
    substituted = value.subs({X: data.bases[0] ** THETA, Y: data.bases[1] ** THETA})
    return sp.latex(substituted).replace(
        r"\theta", data.substitution or data.argument_text
    )


def excluded(data):
    argument = data.substitution or data.argument_text
    base = data.bases[(X, Y).index(data.variable)]
    bounded_base = base**data.power
    low, high = min(bounded_base, 1 / bounded_base), max(bounded_base, 1 / bounded_base)
    html = line(expression(data.univariate, data) + "=0")
    if data.substitution:
        logarithm = (
            (sp.latex(sp.Rational(1, data.power)) if data.power != 1 else "")
            + r"\log_{"
            + sp.latex(base)
            + "}"
            + sp.latex(data.level)
        )
    else:
        logarithm = r"\log_{" + sp.latex(bounded_base) + "}" + sp.latex(data.level)
    html += line(argument + "=" + logarithm)
    html += "<p>Значения синуса и косинуса лежат от −1 до 1. Поэтому степень на этом промежутке ограничена:</p>"
    html += line(r"-1\le " + argument + r"\le1")
    power = r"\left(" + sp.latex(bounded_base) + r"\right)^{" + argument + "}"
    html += line(
        sp.latex(low)
        + r"\le "
        + power
        + r"\le "
        + sp.latex(high)
        + "<"
        + sp.latex(data.level)
    )
    return html + "<p>Следовательно, эта ветвь не имеет решений.</p>"


def zero(data):
    from .exam_trigonometric_power_equality_proof import power

    html = line(
        expression(-data.mixed if data.reverse_mixed else data.mixed, data) + "=0"
    )
    (m, _), (n, _) = sp.Poly(data.mixed, X, Y).terms()
    if data.reverse_mixed:
        m, n = n, m
    ratio = sp.prod(b ** (i - j) for b, i, j in zip(data.bases, m, n))
    divisor = X ** n[0] * Y ** n[1]
    html += "<p>Разделим равенство на положительную степень и объединим степени с одинаковым показателем:</p>"
    html += line(expression(divisor, data) + ">0")
    argument = data.substitution or data.argument_text
    html += line(power(ratio, THETA).replace(r"\theta", argument) + "=1")
    html += line(sp.latex(ratio) + r">0,\quad " + sp.latex(ratio) + r"\ne1")
    html += "<p>Степень с положительным основанием, отличным от единицы, равна единице только при нулевом показателе:</p>"
    return html + line(argument + "=0")


def proof(a, image=""):
    from .exam_trigonometric_proof import candidate_lines

    data = a.power_equality.grouping
    sign = -1 if data.reverse_mixed else 1
    html = line(a.original)
    if data.substitution:
        html += "<p>Введём переменную для общего тригонометрического показателя:</p>"
        html += line(data.substitution + "=" + data.argument_text)
    html += "<p>Разложим основания на множители и соберём степени с одинаковым показателем:</p>"
    html += line(expression(sign * data.positive_factor * data.polynomial, data) + "=0")
    if data.positive_factor != 1:
        html += "<p>Разделим на общий положительный множитель; нули выражения сохранятся:</p>"
        html += line(expression(data.positive_factor, data) + ">0")
    html += line(expression(sign * data.polynomial, data) + "=0")
    html += "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>"
    grouped = sp.Add(
        *(
            sp.Mul(coefficient * X ** m[0] * Y ** m[1], data.univariate, evaluate=False)
            for m, coefficient in sp.Poly(sign * data.mixed, X, Y).terms()
        ),
        evaluate=False,
    )
    html += line(expression(grouped, data) + "=0")
    factors = (sign * v if v == data.mixed else v for v in data.order)
    html += line(
        "".join(r"\left(" + expression(v, data) + r"\right)" for v in factors) + "=0"
    )
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. Рассмотрим обе ветви:</p>"
    html += image
    for branch in data.order:
        html += excluded(data) if branch == data.univariate else zero(data)
    if data.substitution:
        html += "<p>Вернёмся к исходному аргументу:</p>"
    for branch in a.branches:
        html += candidate_lines(
            branch,
            angle=sp.latex(a.scale) + "x" if a.scale != 1 else "x",
            root_scale=a.scale,
        )
    return (
        "<p>Используем свойства положительных степеней и разложим выражение на множители:</p>",
        html,
    )
