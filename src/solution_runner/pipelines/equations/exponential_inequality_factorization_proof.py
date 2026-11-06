"""Keep positive-factor rationalization and both reviewed grouping methods."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expanded as power_sum_text
from .exponential_inequality_quadratic_proof import expression
from .exponential_inequality_reduction_proof import monotonic, sum_terms
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import (
    RELATION,
    domain,
    interval_proof,
    interval_signs_text,
    normalized,
)


def fraction(numerator, denominator):
    return r"\frac{" + numerator + "}{" + denominator + "}"


def linear_denominator(a):
    n = a.numerator
    actual = power(n.base, n.exponent)
    denominator = sp.latex(a.denominator)
    numerator = sum_terms(
        (*((c, power(b, g)) for c, b, g in n.powers), (n.constant, ""))
    )
    expanded = expression(n.stage.original, actual)
    factored = expression(real_factor(n.stage.original, n.stage.zeros), actual)
    positive = fraction(
        expression(polynomial(n.stage.original).LC() * (X - a.negative_root), actual),
        actual,
    )
    html = line(a.formula) + domain(a.stage)
    html += "<p>Рассмотрим отдельно числитель дроби. Приведём степени к одному основанию и запишем точное разложение, сохраняя числовой множитель:</p>"
    html += line(actual + ">0")
    html += line(numerator + "=" + power_sum_text(n, actual, reciprocal=True))
    html += line(
        power_sum_text(n, actual, reciprocal=True) + "=" + fraction(expanded, actual)
    )
    html += line(fraction(expanded, actual) + "=" + fraction(factored, actual))
    html += (
        "<p>Множитель "
        + inline(positive)
        + " положителен при любом действительном x. Поэтому его можно убрать при сравнении знаков исходной дроби:</p>"
    )
    html += line(positive + ">0")
    html += line(
        fraction(expression(X - a.positive_root, actual), denominator)
        + RELATION[a.operator]
        + "0"
    )
    html += line(sp.latex(a.positive_root) + "=" + power(n.base, a.level))
    html += monotonic(n.base)
    html += "<p>Показательная разность имеет тот же знак, что и разность показателей. Сохраняя исходный знаменатель, получаем равносильное неравенство:</p>"
    html += line(a.stage.formula)
    if a.stage.original != a.stage.expression or a.stage.holes:
        html += normalized(a.stage)
    return html + interval_proof(a.stage, "")


def grouping(a):
    base_power = power(a.base, X)
    other_power = power(a.other, X)
    difference = r"\left(" + other_power + "-" + base_power + r"\right)"
    A, B, C = a.coefficients
    pairs = (
        (A, power(a.base**2 * a.other, X)),
        (-A, power(a.base**3, X)),
        (B, power(a.base * a.other, X)),
        (-B, power(a.base**2, X)),
        (C, other_power),
        (-C, base_power),
    )
    grouped = sum_terms(
        (
            (A, power(a.base, 2 * X) + r"\cdot " + difference),
            (B, base_power + r"\cdot " + difference),
            (C, difference),
        )
    )
    quadratic = r"\left(" + expression(a.quadratic.original, base_power) + r"\right)"
    html = "<p>Сгруппируем слагаемые и разложим на множители:</p>"
    html += line(sum_terms(pairs) + RELATION[a.operator] + "0")
    html += line(grouped + RELATION[a.operator] + "0")
    html += line(difference + r"\cdot " + quadratic + RELATION[a.operator] + "0")
    return html, difference, quadratic


def interval_method(a):
    html, _, quadratic = grouping(a)
    base_power, other_power = power(a.base, X), power(a.other, X)
    html += "<p>Решим уравнение, полученное из первого множителя:</p>"
    html += line(
        other_power
        + "="
        + base_power
        + r"\iff "
        + power(sp.cancel(a.other / a.base), X)
        + r"=1\iff x=0"
    )
    html += (
        "<p>Решим уравнение из второго множителя. Положим "
        + inline("t=" + base_power + ">0")
        + ":</p>"
    )
    html += line(quadratic + "=0")
    html += line(expression(a.quadratic.original, "t") + "=0")
    html += line(r",\quad ".join("t=" + sp.latex(t) for t in a.quadratic.zeros))
    for t, _value, roots in a.back:
        html += line(base_power + "=" + sp.latex(t) + r"\iff x=" + sp.latex(roots[0]))
    html += (
        "<p>Итак, левая часть обращается в нуль в точках "
        + inline(r",\ ".join(sp.latex(r) for r in a.stage.zeros))
        + ". Применим метод интервалов, учитывая знаки множителей:</p>"
    )
    html += line(interval_signs_text(a.stage))
    return html + line(r"x\in " + a.answer)


def rationalization_method(a):
    html, difference, _ = grouping(a)
    actual = power(a.base, X)
    factored = expression(real_factor(a.quadratic.original, a.quadratic.zeros), actual)
    html += line(factored + r"\cdot " + difference + RELATION[a.operator] + "0")
    leading = polynomial(a.quadratic.original).LC()
    if leading != 1:
        html += (
            "<p>Убираем положительный числовой множитель "
            + inline(sp.latex(leading))
            + ", не меняя знака неравенства:</p>"
        )
    factors = [
        r"\left(" + actual + "-" + power(a.base, value) + r"\right)"
        for _, value, _ in a.back
    ]
    html += line(r"\cdot ".join((*factors, difference)) + RELATION[a.operator] + "0")
    html += (
        "<p>Применим метод рационализации: заменим каждый множитель выражением с тем же знаком. Основания "
        + inline(sp.latex(a.base) + ">1")
        + " и "
        + inline(sp.latex(sp.cancel(a.other / a.base)) + ">1")
        + "; в разности степеней общий множитель положителен:</p>"
    )
    html += line(a.stage.formula)
    return html + line(r"x\in " + a.answer)


def cube_over_square(a, image=""):
    n = a.numerator
    actual = power(n.base, n.exponent)
    original_numerator = sum_terms(
        (*((c, power(b, g)) for c, b, g in n.powers), (n.constant, ""))
    )
    leading = polynomial(n.stage.original).LC()
    cube = expression((X - a.numerator.stage.zeros[0]) ** 3, actual)
    denominator = sp.latex(a.denominator_factor**2)
    html = line(a.formula) + domain(a.stage)
    html += "<p>Выражение в числителе представляет собой куб разности с положительным числовым множителем. Приведём степени к одному основанию:</p>"
    html += line(original_numerator + "=" + power_sum_text(n, actual))
    html += line(
        power_sum_text(n, actual)
        + "="
        + expression(leading * (X - n.stage.zeros[0]) ** 3, actual)
    )
    html += "<p>Знаменатель — положительный числовой множитель, умноженный на полный квадрат:</p>"
    html += line(
        sp.latex(a.denominator)
        + "="
        + sp.latex(
            sp.Mul(a.denominator_scalar, a.denominator_factor**2, evaluate=False)
        )
    )
    scalar = sp.cancel(leading / a.denominator_scalar)
    html += "<p>После вынесения этих множителей из исходной дроби остаётся положительный коэффициент. Деление на него не меняет знак неравенства:</p>"
    html += line(sp.latex(scalar) + ">0")
    html += line(fraction(cube, denominator) + RELATION[a.operator] + "0")
    html += line(sp.latex(n.stage.zeros[0]) + "=" + power(n.base, a.level))
    html += monotonic(n.base)
    html += "<p>Применим метод рационализации: разность степеней имеет тот же знак, что и разность показателей. Нечётный куб сохраняет этот знак. Знаменатель и его исключённую точку сохраняем:</p>"
    html += line(a.stage.formula)
    html += "<p>Применяем метод интервалов. Нуль числителя имеет кратность 3, поэтому знак при переходе через него меняется. Полюс знаменателя имеет кратность 2: знак не меняется, но сама точка исключена:</p>"
    if a.stage.original != a.stage.expression:
        html += normalized(a.stage)
    html += line(interval_signs_text(a.stage))
    html += image
    html += "<p>Выбираем промежутки с нужным знаком. Исключённую точку знаменателя не включаем; допустимый нуль числителя включаем только при нестрогом неравенстве:</p>"
    return html + line(r"x\in " + a.answer)


def grouped_quadratic(a):
    return (
        line(a.formula)
        + "<p><strong>Первый способ.</strong></p>"
        + interval_method(a)
        + "<p><strong>Второй способ.</strong></p>"
        + rationalization_method(a)
    )


RENDERS = {
    "linear_denominator": linear_denominator,
    "grouped_quadratic": grouped_quadratic,
    "cube_over_square": cube_over_square,
}
