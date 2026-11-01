"""Render each reviewed radical argument and keep its independently certified notes."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_radical_equation import CIRCLE


def family_lines(a):
    from .exam_trigonometric_proof import families

    return "".join(line(text + r",\quad k\in\mathbb Z") for text in families(a))


def half_primary(a):

    t = sp.Symbol("t", real=True)
    data = a.radical_equation
    quartic = sp.expand(sp.rem(data.squared, CIRCLE, S) / (C + 1))
    quartic = sp.cancel(quartic)
    if sp.Poly(quartic, C).LC() < 0:
        quartic = -quartic
    html = line(a.original)
    html += "<p>Сохраним область определения тангенса и корня:</p>"
    html += line(r"\cos\frac{3x}{2}\ne0,\quad 3-\tg^2\frac{3x}{2}\ge0")
    html += "<p>Перенесём косинус вправо. Правая часть положительна, поэтому синус должен быть положительным; при этих условиях возведение в квадрат равносильно:</p>"
    html += line(r"2+\cos x\ge1>0,\quad\sin x>0")
    html += line(r"\sin^2x\left(3-\tg^2\frac{3x}{2}\right)=(2+\cos x)^2")
    html += "<p>Используем формулы тангенса, косинуса тройного и половинного углов:</p>"
    html += line(r"\tg^2\alpha=\frac1{\cos^2\alpha}-1")
    html += line(
        r"\cos^2\frac{3x}{2}=\cos^2\frac{x}{2}\left(4\cos^2\frac{x}{2}-3\right)^2=\frac{(1+\cos x)(2\cos x-1)^2}{2}"
    )
    html += line(r"t=\cos x,\quad -1\le t\le1,\quad t\ne-1,\quad t\ne\frac12")
    html += line(r"(1-t^2)\left(4-\frac2{(1+t)(2t-1)^2}\right)=(2+t)^2")
    html += "<p>Умножаем только на ненулевые знаменатели в исходной области определения:</p>"
    html += line(sp.latex(quartic.subs(C, t)) + "=0")
    html += line(sp.latex(sp.factor(quartic.subs(C, t))) + "=0")
    html += line(r"5t^2-6t+2:\quad D=36-40=-4<0")
    html += line(r"t=-\frac12\quad\Longleftrightarrow\quad\cos x=-\frac12")
    html += (
        "<p>Оставляем ветвь с положительным синусом и проверяем исходный радикал:</p>"
    )
    html += line(r"\tg\frac{3x}{2}=0,\quad 3-\tg^2\frac{3x}{2}=3>0")
    html += family_lines(a)
    return (
        "<p>Решим уравнение через косинус после равносильного возведения в квадрат:</p>",
        html,
    )


def amgm_primary(a):
    from .exam_trigonometric_proof import formula

    data = a.radical_equation
    html = line(a.original)
    html += "<p>Оба тригонометрических отношения должны быть определены. Вместе с областью определения корня это даёт:</p>"
    html += line(r"\sin x\ne0,\quad\cos x\ne0,\quad\sin x\cos x>0")
    html += "<p>Используем определения отношений и основное тригонометрическое тождество:</p>"
    html += line(r"\ctg x=\frac{\cos x}{\sin x},\quad\tg x=\frac{\sin x}{\cos x}")
    html += line(
        formula(2 * data.unreduced_right / data.multiplier) + r"=2\sqrt{\sin x\cos x}"
    )
    html += line(r"\sin^2x+\cos^2x=1")
    html += line(r"\sin x+\cos x=2\sqrt{\sin x\cos x}")
    html += "<p>Синус и косинус имеют один знак, а их сумма неотрицательна. Поэтому обе функции положительны. Выделим полный квадрат:</p>"
    html += line(r"\sin x>0,\quad\cos x>0")
    html += line(r"(\sqrt{\sin x}-\sqrt{\cos x})^2=0")
    html += line(
        r"\sqrt{\sin x}=\sqrt{\cos x}\quad\Longleftrightarrow\quad\sin x=\cos x>0"
    )
    html += family_lines(a)
    return (
        "<p>Преобразуем уравнение при сохранении исходной области определения:</p>",
        html,
    )


def extremal_primary(a):
    multiple = a.radical_equation.multiple
    sign = sp.sin(multiple * sp.pi / 2)
    parity = 1 if sign == 1 else 0
    html = line(a.original)
    html += "<p>Корень неотрицателен. Сохраним знак правой части перед возведением в квадрат:</p>"
    html += line(r"\cos x\le0")
    html += line(r"\cos2x-\sin " + str(multiple) + r"x=4\cos^2x")
    html += line(r"\sin " + str(multiple) + r"x+\cos2x=-2")
    html += "<p>Каждое слагаемое не меньше −1. Сумма равна −2 только при одновременном равенстве обоих слагаемых −1:</p>"
    html += line(r"\sin " + str(multiple) + r"x=-1,\quad\cos2x=-1")
    html += line(
        r"\cos2x=-1\quad\Longleftrightarrow\quad x=\frac\pi2+\pi k,\quad k\in\mathbb Z"
    )
    html += line(
        r"\sin\left("
        + str(multiple)
        + r"\left(\frac\pi2+\pi k\right)\right)="
        + sp.latex(sign)
        + r"\cdot(-1)^k"
    )
    html += (
        "<p>Подходят "
        + ("нечётные" if parity else "чётные")
        + " значения старого параметра. Введём новый целый параметр без ограничения чётности:</p>"
    )
    html += line("k=2n+" + str(parity) + r",\quad n\in\mathbb Z")
    html += "<p>После сдвига на целое число периодов и переобозначения параметра получаем:</p>"
    html += family_lines(a)
    html += "<p>Все найденные корни обращают косинус и подкоренное выражение в нуль, поэтому удовлетворяют исходному уравнению. Граница области определения сохраняется.</p>"
    html += line(r"\cos x=0,\quad\cos2x-\sin " + str(multiple) + r"x=0")
    return (
        "<p>Используем знак корня и нижние границы тригонометрических функций:</p>",
        html,
    )


def proof(a):
    from .exam_trigonometric_safe_square_proof import proof as safe_square

    return {
        "safe_square": safe_square,
        "half_tangent": half_primary,
        "amgm": amgm_primary,
        "extremal": extremal_primary,
    }[a.radical_equation.kind](a)


def notes(a):
    if a.radical_notes[1] == "amgm":
        return tangent_note(a)
    return half_notes(a)


def tangent_note(a):
    html = "<p>Приведём другое решение уравнения после сведения к сумме синуса и косинуса.</p>"
    html += "<p>Синус и косинус положительны. Делим только на положительный косинус и вносим его под корень:</p>"
    html += line(r"\tg x-2\sqrt{\tg x}+1=0")
    html += line(
        r"(\sqrt{\tg x}-1)^2=0\quad\Longleftrightarrow\quad\sqrt{\tg x}=1\quad\Longleftrightarrow\quad\tg x=1"
    )
    html += line(r"\cos x>0")
    return html + family_lines(a)


def half_notes(a):
    t = sp.Symbol("t", real=True)
    raw = sp.expand(sp.rem(a.radical_equation.squared, CIRCLE, S)).subs(C, t)
    if sp.Poly(raw, t).LC() < 0:
        raw = -raw
    html = "<p>Приведём идею другого решения. Выразим квадрат тангенса через косинус тройного угла, сохранив исходную область определения и положительность синуса:</p>"
    html += line(
        r"\tg^2\frac{3x}{2}=\frac{1-\cos3x}{1+\cos3x},\quad\cos3x=4\cos^3x-3\cos x"
    )
    html += line(r"t=\cos x,\quad1+4t^3-3t\ne0,\quad\sin x>0")
    html += line(r"\left(3-\frac{1-4t^3+3t}{1+4t^3-3t}\right)(1-t^2)=(2+t)^2")
    html += line(sp.latex(raw) + "=0")
    html += line(sp.latex(sp.factor(raw)) + "=0")
    html += "<p>Значение t=−1 обращает исходный знаменатель в нуль. Квадратный множитель с отрицательным дискриминантом не имеет вещественных корней. Остаётся:</p>"
    html += line(r"t=-\frac12,\quad\sin x>0")
    html += family_lines(a)
    third = "<p>Перенесём косинус вправо и вновь возведём в квадрат при положительном синусе. Сгруппируем слагаемые иначе:</p>"
    third += line(r"-\sin^2x\,\tg^2\frac{3x}{2}=(1+2\cos x)^2")
    third += "<p>Левая часть неположительна, а правая неотрицательна. Поэтому обе части должны равняться нулю:</p>"
    third += line(r"1+2\cos x=0,\quad\sin^2x\,\tg^2\frac{3x}{2}=0")
    third += line(r"\cos x=-\frac12,\quad\sin x>0")
    third += family_lines(a)
    q, p = a.series[0]
    k = sp.Symbol("k", integer=True)
    argument = sp.expand(3 * (q + p * k) * sp.pi / 2)
    third += line(r"\tg\left(" + sp.latex(argument) + r"\right)=0")
    third += "<p>Следовательно, вторая часть системы и исходное уравнение выполняются для всех членов найденной серии.</p>"
    return (
        html
        + '<section data-content-kind="solution" data-solution-title="Альтернативное решение.">'
        + third
        + "</section>"
    )


def numeric_selection(a):
    from .exam_scalar import compare
    from .exam_trigonometric_inequalities import inequality_selection

    html = "<p>Для числовых границ обоснуем переход к целым индексам строгими оценками числа π:</p>"
    html += line(r"3<\pi<\frac{22}{7}")
    lo, hi, lc, uc = a.bounds
    for q, p, start, end, _ in a.selections:
        lower, upper = sp.simplify((lo - q) / p), sp.simplify((hi - q) / p)
        left_sign, right_sign = ("<", r"\le ") if lc else (r"\le ", "<")
        if compare(lower, sp.Integer(start - 1)) < (1 if lc else 0) or compare(
            lower, sp.Integer(start)
        ) > (0 if lc else -1):
            raise UnsupportedCondition("the lower integer-index certificate changed")
        html += line(
            str(start - 1) + left_sign + sp.latex(lower) + right_sign + str(start)
        )
        left_sign, right_sign = (r"\le ", "<") if uc else ("<", r"\le ")
        if compare(upper, sp.Integer(end)) < (0 if uc else 1) or compare(
            upper, sp.Integer(end + 1)
        ) > (-1 if uc else 0):
            raise UnsupportedCondition("the upper integer-index certificate changed")
        html += line(str(end) + left_sign + sp.latex(upper) + right_sign + str(end + 1))
    return html + inequality_selection(a)
