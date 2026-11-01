"""Follow the parent's cancellations while keeping every original quotient pole."""

import re

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_original_quotients import source_branches


def domain(a):
    from .exam_trigonometric_proof import formula

    html = "<p>До сокращения запишем исходную область определения:</p>"
    for pole in a.poles:
        text = (
            r"\cos2x"
            if a.original_quotient.method == "double_square" and pole == 2 * C * C - 1
            else formula(pole)
        )
        html += line(text + r"\ne0")
    for v in (S, C):
        from .exam_trigonometric_original_quotients import nonzero

        if nonzero(v, a.poles) and v not in a.poles:
            html += line(formula(v) + r"\ne0")
    return html


def ratio(a):
    from .exam_trigonometric_proof import formula

    d = a.original_quotient
    html = "<p>Упростим правую часть на исходной области определения:</p>"
    for text, value in a.identities:
        if value not in (S, C) and r"\tg" not in text:
            html += line(text + "=" + formula(value))
    numerator, denominator = sp.fraction(d.source_right)
    html += line(formula(d.source_right))
    html += line(formula(S * S + C * C) + "=1")
    numerator = sp.rem(numerator, S * S + C * C - 1, C)
    fraction = sp.Mul(
        numerator, sp.Pow(denominator, -1, evaluate=False), evaluate=False
    )
    html += line(formula(fraction))
    html += (
        "<p>Сокращаем на синус только потому, что по исходной ОДЗ он не равен нулю:</p>"
    )
    html += line(formula(d.right))
    weight = sp.cancel(d.right * C / S)
    html += line(formula(d.right) + "=" + sp.latex(weight) + r"\tg x")
    for text, value in a.identities:
        if value == S or r"\tg" in text:
            html += line(text + "=" + formula(value))
    html += line(formula(sp.expand(d.left)) + "=" + formula(d.right))
    return html


def powered(text, degree):
    return re.sub(r"^(\\(?:sin|cos))", lambda m: m[1] + "^{" + str(degree) + "}", text)


def fourth(a):
    from .exam_trigonometric_log_equality import original_text
    from .exam_trigonometric_proof import formula
    from .power_arithmetic import balanced, clean

    d = a.original_quotient
    sine, cosine, weight = d.half
    html = "<p>В исходной ОДЗ общий знаменатель определён и не равен нулю. Поэтому приравняем числители:</p>"
    numerators = [
        original_text(balanced(clean(side), 5)[0])
        for side in a.original.removesuffix(".").split("=")
    ]
    html += line(numerators[0] + "=" + numerators[1])
    html += "<p>Разложим разность четвёртых степеней как разность квадратов:</p>"
    difference = powered(sine, 2) + "-" + powered(cosine, 2)
    total = powered(sine, 2) + "+" + powered(cosine, 2)
    html += line(
        numerators[1]
        + "="
        + sp.latex(weight)
        + r"\left("
        + difference
        + r"\right)\left("
        + total
        + r"\right)"
    )
    html += line(total + "=1")
    html += line(difference + r"=-\cos x")
    html += line(r"\sin2x=2\sin x\cos x")
    html += line(formula(d.left) + "=" + formula(d.right))
    return html


def square(a):
    from .exam_trigonometric_proof import formula, polynomial

    d = a.original_quotient
    weight = sp.cancel(d.right * S / ((2 * C * C - 1) * C))
    html = "<p>На исходной ОДЗ используем определения тангенса и котангенса:</p>"
    html += line(
        r"\frac{\sin2x}{\cos2x}="
        + sp.latex(weight)
        + r"\cos2x\cdot\frac{\cos x}{\sin x}"
    )
    html += line(r"\sin2x=2\sin x\cos x")
    html += "<p>Умножим на исходные ненулевые знаменатели и перенесём слагаемые:</p>"
    html += line(r"2\sin^2x\cos x=" + sp.latex(weight) + r"\cos^22x\cos x")
    coefficient = "" if d.square == 1 else sp.latex(d.square) + r"\cdot"
    html += line(r"\cos x\left(\cos^22x-" + sp.latex(d.square**2) + r"\sin^2x\right)=0")
    html += line(
        r"\cos x\left(\cos2x-"
        + coefficient
        + r"\sin x\right)\left(\cos2x+"
        + coefficient
        + r"\sin x\right)=0"
    )
    html += "<p>Рассмотрим три нулевых множителя. На косинус не делим: его нулевые значения допустимы в исходном уравнении.</p>"
    cases = source_branches(d, a.allow_inverse)
    html += polynomial(cases[0])
    for sign, b in zip((-1, 1), cases[1:], strict=True):
        html += line(
            r"\cos2x" + ("-" if sign == -1 else "+") + coefficient + r"\sin x=0"
        )
        html += line(r"\cos2x=1-2\sin^2x")
        html += polynomial(b, allow_inverse=a.allow_inverse)
    html += "<p>Серии, полученные при синусе 1 и −1, уже входят в ветвь нулевого косинуса. При объединении записываем каждую серию один раз.</p>"
    for pole in a.poles:
        values = sp.FiniteSet(
            *(
                sp.simplify(pole.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
                for q in a.residues
            )
        )
        text = r"\cos2x" if pole == 2 * C * C - 1 else formula(pole)
        html += line(
            text + r"\in" + sp.latex(values) + r",\quad 0\notin" + sp.latex(values)
        )
    return html


def proof(a):
    from .exam_trigonometric_proof import families, formula, polynomial

    d = a.original_quotient
    html = line(a.original) + domain(a)
    if d.method == "double_square":
        html += square(a)
    else:
        html += ratio(a) if d.method == "cancel_ratio" else fourth(a)
        if d.denominator != 1:
            html += "<p>Умножим на знаменатель, ненулевой по исходной ОДЗ:</p>"
            html += line(formula(d.denominator) + r"\ne0")
        html += line(formula(sp.factor(d.numerator, extension=True)) + "=0")
        html += line(formula(d.divide) + r"\ne0")
        html += "<p>Разделим на этот заведомо ненулевой множитель:</p>"
        for b in a.branches:
            html += polynomial(b, allow_inverse=a.allow_inverse)
    html += "<p>С учётом исходной области определения получаем:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Решим уравнение с сохранением исходной ОДЗ:</p>", html
