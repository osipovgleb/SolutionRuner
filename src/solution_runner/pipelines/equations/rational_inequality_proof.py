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
    if a.presentation_method == "cancelled_quadratic_sum":
        from .rational_inequality_algebraic_methods import real_factor

        numerator = real_factor(numerator, a.zeros)
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


def interval_signs_text(a):
    boundaries = (-sp.oo, *a.points, sp.oo)
    entries = []
    for lo, hi, sign in zip(boundaries, boundaries[1:], a.signs):
        entries.append(
            set_latex(sp.Interval.open(lo, hi))
            + r":\ "
            + {1: "+", -1: "-", 0: "0"}[sign]
        )
    return r";\quad ".join(entries)


def interval_proof(a, image):
    html = "<p>Применяем метод интервалов. Отмечаем нули числителя и все исключённые точки. Знак на каждом промежутке определяем подстановкой внутренней точки:</p>"
    html += line(interval_signs_text(a))
    html += image
    html += "<p>Выбираем промежутки с нужным знаком. При нестрогом неравенстве включаем допустимые нули числителя; точки, исключённые исходными знаменателями, не включаем.</p>"
    return html + line(r"x\in " + set_latex(a.solution))


def factor_justification(a, method):
    from .rational_inequality_factor_methods import (
        positive_quadratics,
        square_parameters,
    )

    if method == "common_square":
        _, _, _, root = square_parameters(a)
        html = "<p>Общий квадрат не сокращаем: он обращается в нуль в допустимой точке. При нестрогом неравенстве эту точку необходимо проверить и сохранить:</p>"
        return html + line("x=" + latex(root))
    if method != "quartic_cancel":
        return ""
    html = ""
    for factor, completed in positive_quadratics(a):
        html += "<p>Квадратный множитель положителен при всех действительных x, поэтому не создаёт нулей и не меняет знак произведения:</p>"
        html += line(latex(factor) + "=" + latex(completed) + ">0")
    return html


def render(a, method, image=""):
    from .rational_inequality_algebraic_methods import presentation
    from .rational_inequality_algebraic_proof import vieta

    a = presentation(a, method)
    if method == "vieta_quadratic":
        return vieta(a, image)
    identities, steps = prepare(a, method)
    lead = {
        "long_division": "Имеем:",
        "factor_cancelled": "Перепишем неравенство в виде:",
        "square_numerator": "Преобразуем неравенство:",
        "cancelled_quadratic_sum": "Преобразуем неравенство:",
    }.get(method, "Решим неравенство методом интервалов:")
    html = "<p>" + lead + "</p>" + line(a.formula) + domain(a)
    if identities:
        html += "<p>Выделим целую часть каждой дроби делением многочленов:</p>"
        html += "".join(line(text) for text, _, _ in identities)
        html += "<p>Целые части в сумме совпадают с правой частью и сокращаются:</p>"
    else:
        html += {
            "cancelled_fraction": "<p>Перенесём 1 в левую часть и вычтем её из последней дроби. Затем приведём две последние дроби к общему знаменателю и объединим с x:</p>",
            "quartic_cancel": "<p>Разложим числитель и знаменатель первой дроби на множители. Перенесём правую часть в дробь с линейным знаменателем, сократим общий множитель первой дроби и объединим числители. Исходное исключение сохраняем:</p>",
            "common_square": "<p>Разложим на множители и вынесем общий квадрат за скобку. Затем объединим выражения в скобках и применим метод интервалов:</p>",
            "fraction_division": "<p>На исходной области определения разложим общие множители, если они есть. Выделим целые части дробей делением многочленов; они сократятся. Оставшиеся дроби приведём к общему знаменателю, сохраняя исходные исключения:</p>",
            "degree_division": "<p>Делением многочленов выделим целую часть первой дроби и сократим её с многочленом справа. Объединим дроби с вложенными знаменателями, затем приведём оставшиеся дроби к общему знаменателю:</p>",
            "split_cancel": "<p>Перенесём все слагаемые влево. Если целые части дробей сокращаются, выделим их делением многочленов. В квадратной дроби выделим часть числителя, сокращающую встречную дробь, и оставшийся общий множитель. Исходные исключения сохраняем:</p>",
            "quadratic_right": "<p>На исходной области определения запишем правую часть дробью с тем же знаменателем. Перенесём её влево и разложим полученный числитель на множители:</p>",
            "cubic_cancel": "<p>Представим многочлен и правую часть дробями с исходным знаменателем. После приведения к общему знаменателю кубические члены сократятся:</p>",
            "square_zero": "<p>Перенесём правую часть влево и вычтем её из дроби. Затем приведём многочлен и оставшуюся дробь к общему знаменателю. Множитель x² сохраняем: деление на него могло бы потерять решение x=0:</p>",
            "quadratic_denominators": "<p>Разложим квадратные знаменатели на множители, перенесём правую часть влево и приведём дроби к общему знаменателю. При сокращении сохраняем ограничения исходных знаменателей:</p>",
            "sum_fractions": "<p>На области определения приведём дроби к общему знаменателю и раскроем скобки в числителе:</p>",
            "factor_cancelled": "<p>Разложим многочлены на множители, приведём дроби к общему знаменателю и вынесем общий множитель в числителе. Затем используем разность квадратов:</p>",
            "square_numerator": "<p>Перенесём правую часть влево и объединим выражения в одну дробь на исходной области определения:</p>",
            "opposite_fractions": "<p>На исходной области определения приведём дроби и правую часть к общему знаменателю. Затем найдём корни числителя и разложим его на множители:</p>",
            "cancelled_quadratic_sum": "<p>Заменим разность левой и правой частей противоположной и изменим знак неравенства. Объединим правую часть исходного неравенства в одну дробь, разложим многочлены на множители и сократим общий множитель, сохраняя исходные исключения:</p>",
        }.get(method, "")
    html += "".join(line(step.text + RELATION[a.operator] + "0") for step in steps)
    if method != "opposite_fractions":
        html += normalized(a, already_factored=method == "factor_cancelled")
    return html + factor_justification(a, method) + interval_proof(a, image)
