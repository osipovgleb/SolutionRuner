"""Parent square-root, half-discriminant and Vieta steps for water trips."""

import sympy as sp

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_models import X


def cleared_equation(a):
    denominator = sp.together(a.balance.left - a.balance.right).as_numer_denom()[1]
    sides = [
        sp.cancel(side * denominator) for side in (a.balance.left, a.balance.right)
    ]
    return line("=".join(sp.latex(side, symbol_names={X: "u"}) for side in sides))


def square_steps(a):
    poly = sp.Poly(a.polynomial, X)
    square = -poly.nth(0) / poly.nth(2)
    html = "<p>При указанных ограничениях знаменатели положительны. Избавимся от них и выразим квадрат неизвестной скорости:</p>"
    html += cleared_equation(a)
    html += line("u^2=" + n(square))
    html += line(
        "u=\\pm\\sqrt{"
        + n(square)
        + r"}\in\left\{"
        + ";".join(n(r) for r in a.roots)
        + r"\right\}"
    )
    return (
        html
        + "<p>Отрицательный корень не подходит по смыслу задачи. Положительный корень удовлетворяет ограничениям скоростей:</p>"
        + line("u=" + n(a.root))
    )


def even_steps(a, *, note=False):
    poly = sp.Poly(a.polynomial, X)
    scaled = bool(poly.nth(1) % 2)
    if scaled:
        poly *= 2
    c2, c1, c0 = (poly.nth(i) for i in (2, 1, 0))
    half = c1 / 2
    reduced = half**2 - c2 * c0
    html = "<p>Воспользуемся формулой корней квадратного уравнения с чётным коэффициентом при неизвестной:</p>"
    if scaled:
        html += "<p>Запишем эквивалентное уравнение с чётным коэффициентом при u:</p>"
    html += line(sp.latex(poly.as_expr(), symbol_names={X: "u"}) + "=0")
    html += line(r"u=\frac{-\frac{b}{2}\pm\sqrt{(\frac{b}{2})^2-ac}}{a}")
    html += line(
        "D_1=(" + n(half) + ")^2-(" + n(c2) + ")\\cdot(" + n(c0) + ")=" + n(reduced)
    )
    html += line(
        "u="
        + frac("-(" + n(half) + r")\pm\sqrt{" + n(reduced) + "}", n(c2))
        + r"\in\left\{"
        + ";".join(n(r) for r in a.roots)
        + r"\right\}"
    )
    html += (
        "<p>Выбираем корень, при котором обе скорости движения положительны и выполнены ограничения:</p>"
        + line("u=" + n(a.root))
    )
    if note:
        html += "<p><b>Примечание.</b> Для чётного коэффициента b вычисления упрощает использование b/2 вместо b. Если нужно, уравнение можно предварительно умножить на 2. Формула остаётся той же:</p>"
        html += line(r"u=\frac{-b/2\pm\sqrt{(b/2)^2-ac}}{a}")
    return html


def square_completion(a):
    poly = sp.Poly(a.polynomial, X)
    if poly.nth(1) % 2:
        poly *= 2
    reduced = (poly.nth(1) / 2) ** 2 - poly.nth(2) * poly.nth(0)
    root = sp.sqrt(reduced)
    factor = 1
    while root % (2 * factor) == 0:
        factor *= 2
    core = root / factor
    base = 10 * (core // 10)
    tail = core - base
    html = "<p>Покажем, как распознать полный квадрат под корнем. Выделим квадратный множитель и представим оставшееся число как квадрат суммы:</p>"
    html += line(n(reduced) + "=" + n(factor**2) + r"\cdot" + n(core**2))
    html += line(
        n(core**2)
        + "="
        + n(base)
        + "^2+2\\cdot"
        + n(base)
        + r"\cdot"
        + n(tail)
        + "+"
        + n(tail)
        + "^2=("
        + n(base)
        + "+"
        + n(tail)
        + ")^2"
    )
    return html + line(
        r"\sqrt{" + n(reduced) + "}=" + n(factor) + r"\cdot" + n(core) + "=" + n(root)
    )


def vieta(a):
    poly = sp.Poly(a.polynomial, X)
    positive, negative = a.roots
    html = "<p><b>Примечание.</b> Корни можно найти по теореме, обратной теореме Виета. Их сумма и произведение должны равняться:</p>"
    html += line(
        "u_1+u_2="
        + n(-poly.nth(1) / poly.nth(2))
        + "="
        + n(positive)
        + "+("
        + n(negative)
        + ")"
    )
    return html + line(
        "u_1u_2="
        + n(poly.nth(0) / poly.nth(2))
        + "="
        + n(positive)
        + r"\cdot("
        + n(negative)
        + ")"
    )
