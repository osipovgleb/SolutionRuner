"""Keep the parent's substitution, interval work, inverse map and centering remark."""

import sympy as sp

from ..probability.common import line
from .rational_inequality import set_latex
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_methods import latex
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION


def display(value, variable):
    return latex(value.xreplace({X: sp.Symbol(variable, real=True)}))


def fraction(numerator, denominator, variable):
    return (
        r"\frac{"
        + display(numerator, variable)
        + "}{"
        + display(denominator, variable)
        + "}"
    )


def common_fraction(values, bound):
    denominator = sp.factor(sp.lcm([d for _, d in values]))
    pieces = [
        sp.Mul(n, sp.factor(sp.cancel(denominator / d)), evaluate=False)
        for n, d in values
    ]
    pieces.append(sp.Mul(-bound, denominator, evaluate=False))
    numerator = sp.Add(*pieces, evaluate=False)
    return numerator, denominator


def inequality(values, bound, operator, variable):
    return (
        "+".join(fraction(n, d, variable) for n, d in values)
        + RELATION[operator]
        + latex(bound)
    )


def return_to_x(m):
    variable = sp.Symbol(m.variable, real=True)
    html = "<p>Возвращаясь к исходной переменной, получаем:</p>"
    html += line("x=" + latex(sp.expand((variable - m.offset) / m.scale)))
    return html + line(r"x\in " + set_latex(m.original.solution))


def affine_radical(m, image):
    a = m.stage
    html = "<p>Сделаем замену переменной:</p>" + line(
        "z=" + latex(m.scale * X + m.offset)
    )
    html += line(inequality(m.fractions, a.right.value, a.operator, "z"))
    html += "<p>Исходные знаменатели должны быть ненулевыми. На этой области приведём дроби и правую часть к общему знаменателю:</p>"
    html += line(r",\quad ".join(r"z\ne " + latex(p) for p in a.poles))
    numerator, denominator = common_fraction(m.fractions, a.right.value)
    html += line(
        fraction(numerator, sp.factor(denominator), "z") + RELATION[a.operator] + "0"
    )
    html += line(
        fraction(sp.expand(numerator), sp.factor(denominator), "z")
        + RELATION[a.operator]
        + "0"
    )
    ratio = sp.cancel(a.original / a.expression)
    if ratio != 1:
        adjective = "отрицательный" if ratio < 0 else "положительный"
        result = "меняется" if ratio < 0 else "сохраняется"
        html += (
            "<p>Делим обе части на "
            + adjective
            + " множитель "
            + latex(ratio)
            + ": знак неравенства "
            + result
            + ".</p>"
        )
    n, d = sp.fraction(a.expression)
    html += line(
        fraction(real_factor(n, a.zeros), sp.factor(d), "z")
        + RELATION[a.sign_operator]
        + "0"
    )
    html += (
        "<p>Методом интервалов выбираем подходящие промежутки; нули знаменателей исключаем:</p>"
        + image
    )
    html += line(r"z\in " + set_latex(a.solution)) + return_to_x(m)
    midpoint = sp.simplify(sum(a.poles) / 2)
    centered = tuple(
        (sp.expand(n.subs(X, X + midpoint)), sp.expand(d.subs(X, X + midpoint)))
        for n, d in m.fractions
    )
    html += "<p>Замечание. Преобразования можно упростить, расположив нули знаменателей симметрично относительно нуля. Введём переменную:</p>"
    html += line("u=" + display(X - midpoint, "z"))
    html += line(inequality(centered, a.right.value, a.operator, "u"))
    n, d = common_fraction(centered, a.right.value)
    html += line(fraction(n, sp.expand(d), "u") + RELATION[a.operator] + "0")
    return html


def reciprocal_square(m, image):
    bound = sp.sqrt(m.original.right.value)
    html = (
        "<p>Сделаем замену переменной и сохраним ограничение исходного знаменателя:</p>"
    )
    html += line("t=" + latex(m.scale * X + m.offset) + r",\quad t\ne0")
    html += line(r"\left(\frac{1}{t}+t\right)^2\le" + latex(m.original.right.value))
    html += "<p>Квадрат не превосходит указанного числа тогда и только тогда, когда выражение лежит между противоположными квадратными корнями:</p>"
    html += line(latex(-bound) + r"\le\frac{1}{t}+t\le" + latex(bound))
    html += line(latex(-2 * bound) + r"\le\frac{2t^2+2}{t}\le" + latex(2 * bound))
    rows = []
    for a in m.rows:
        numerator, denominator = sp.fraction(a.expression)
        rows.append(
            fraction(numerator, denominator, "t") + RELATION[a.sign_operator] + "0"
        )
    html += line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")
    html += (
        "<p>Решим каждое неравенство методом интервалов и пересечём полученные множества:</p>"
        + image
    )
    html += line(
        r"\begin{cases}"
        + r"\\".join(r"t\in " + set_latex(a.solution) for a in m.rows)
        + r"\end{cases}"
    )
    html += line(r"t\in " + set_latex(m.stage.solution))
    intervals = sorted(m.stage.solution.args, key=lambda interval: interval.start)
    if (
        len(intervals) == 2
        and intervals[0].start == -intervals[1].end
        and intervals[0].end == -intervals[1].start
    ):
        html += line(latex(intervals[1].start) + r"\le|t|\le" + latex(intervals[1].end))
    return html + return_to_x(m)


METHODS = {"affine_radical": affine_radical, "reciprocal_square": reciprocal_square}


def render(model, method, image):
    return METHODS[method](model, image)
