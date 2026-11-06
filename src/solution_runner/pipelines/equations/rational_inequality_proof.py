"""Render the reviewed algebra, exact signs and original-domain intersection."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .rational_inequality import set_latex
from .rational_inequality_methods import fraction, latex, prepare

RELATION = {"<=": r"\le", ">=": r"\ge", "<": "<", ">": ">"}


def domain(a):
    if not a.poles:
        return "<p>Выражение определено при всех действительных значениях x.</p>"
    return "<p>Исходные знаменатели должны быть ненулевыми:</p>" + line(
        r",\quad ".join("x\\ne " + latex(point) for point in a.poles)
    )


def normalized(a, *, already_factored=False):
    numerator, denominator = sp.fraction(a.expression)
    expression = fraction(sp.factor(numerator), sp.factor(denominator))
    relation = expression + RELATION[a.sign_operator] + "0"
    if a.holes:
        relation = (
            r"\begin{cases}"
            + relation
            + r"\\"
            + r",\quad ".join("x\\ne " + latex(p) for p in a.holes)
            + r"\end{cases}"
        )
    ratio = sp.cancel(a.original / a.expression) if a.expression != 0 else sp.Integer(1)
    if ratio < 0:
        html = (
            "<p>Делим обе части неравенства на отрицательный множитель "
            + inline(latex(ratio))
            + "; знак неравенства меняется:</p>"
        )
    elif ratio != 1:
        html = (
            "<p>Делим обе части неравенства на положительный множитель "
            + inline(latex(ratio))
            + "; знак неравенства сохраняется:</p>"
        )
    else:
        html = (
            ""
            if already_factored
            else "<p>Разложим на множители и запишем равносильное неравенство:</p>"
        )
    if a.holes:
        html += "<p>Сокращение общего множителя сохраняет ограничения исходных знаменателей:</p>"
    return html + line(relation)


def interval_proof(a, image):
    html = "<p>Применяем метод интервалов. Отмечаем нули числителя и все исключённые точки. Знак на каждом промежутке определяем подстановкой внутренней точки:</p>"
    boundaries = (-sp.oo, *a.points, sp.oo)
    entries = []
    for lo, hi, sign in zip(boundaries, boundaries[1:], a.signs):
        entries.append(
            set_latex(sp.Interval.open(lo, hi))
            + r":\ "
            + {1: "+", -1: "-", 0: "0"}[sign]
        )
    html += line(r";\quad ".join(entries))
    html += image
    html += "<p>Выбираем промежутки с нужным знаком. При нестрогом неравенстве включаем допустимые нули числителя; точки, исключённые исходными знаменателями, не включаем.</p>"
    return html + line(r"x\in " + set_latex(a.solution))


def render(a, method, image=""):
    identities, steps = prepare(a, method)
    lead = {
        "long_division": "Имеем:",
        "factor_cancelled": "Перепишем неравенство в виде:",
        "square_numerator": "Преобразуем неравенство:",
    }.get(method, "Решим неравенство методом интервалов:")
    html = "<p>" + lead + "</p>" + line(a.formula) + domain(a)
    if identities:
        html += "<p>Выделим целую часть каждой дроби делением многочленов:</p>"
        html += "".join(line(text) for text, _, _ in identities)
        html += "<p>Целые части в сумме совпадают с правой частью и сокращаются:</p>"
    else:
        html += {
            "cancelled_fraction": "<p>Перенесём 1 в левую часть и вычтем её из последней дроби. Затем приведём две последние дроби к общему знаменателю и объединим с x:</p>",
            "sum_fractions": "<p>На области определения приведём дроби к общему знаменателю и раскроем скобки в числителе:</p>",
            "factor_cancelled": "<p>Разложим многочлены на множители, приведём дроби к общему знаменателю и вынесем общий множитель в числителе. Затем используем разность квадратов:</p>",
            "square_numerator": "<p>Перенесём правую часть влево и объединим выражения в одну дробь на исходной области определения:</p>",
        }.get(method, "")
    html += "".join(line(step.text + RELATION[a.operator] + "0") for step in steps)
    html += normalized(a, already_factored=method == "factor_cancelled")
    return html + interval_proof(a, image)
