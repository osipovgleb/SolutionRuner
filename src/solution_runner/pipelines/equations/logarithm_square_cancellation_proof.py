"""Preserve base-square cancellation and all three methods of the square-factor parent."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_reduction_proof import sum_terms
from .logarithm_product_cancellation_proof import logarithm
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison


def shape(a, degree):
    if (
        len(a.atoms) != 2
        or a.scalar != 1
        or a.multiplier != 1
        or any(arg.denominator != 1 or arg.coefficient != 1 for arg in a.arguments)
    ):
        raise UnsupportedCondition(
            "this parent needs two monic polynomial arguments with a common square"
        )
    if len(a.arguments[1].factors) != 1 or a.arguments[1].factors[0][1] != degree:
        raise UnsupportedCondition(
            "the second argument must be the reviewed pure affine power"
        )
    factor = a.arguments[1].factors[0][0]
    residual = sp.cancel(a.arguments[0].value / factor**2)
    if (
        sp.degree(factor, X) != 1
        or not residual.is_polynomial(X)
        or sp.degree(residual, X) != 1
        or sp.cancel(residual - a.reduced) != 0
    ):
        raise UnsupportedCondition(
            "the cubic must have the same square times the residual affine factor"
        )
    zero = sp.solve(factor, X)[0]
    expected_domain = comparison(residual, ">").solution - sp.FiniteSet(zero)
    if expected_domain != a.domain:
        raise UnsupportedCondition(
            "the original domain must retain the vanished square exclusion"
        )
    return factor, residual, zero


def system(a, factor, condition):
    return line(
        r"\begin{cases}" + sp.latex(factor) + r"\ne0\\" + condition + r"\end{cases}"
    )


def render_base_square(a):
    factor, residual, _zero = shape(a, 4)
    if not (
        a.base < 1
        and a.atoms[1].base == a.base**2
        and a.coefficients == (1, -1)
        and a.constant == 0
        and a.operator == "<="
    ):
        raise UnsupportedCondition(
            "the reviewed decreasing base-square comparison is required"
        )
    square = sp.Pow(factor, 2, evaluate=False)
    q = sp.expand(factor * residual)
    p = sp.Poly(factor, X)
    grouped = sum_terms(
        [
            (p.nth(1), r"x\left(" + sp.latex(q) + r"\right)"),
            (p.nth(0), r"\left(" + sp.latex(q) + r"\right)"),
        ]
    )
    html = "<p>В левой части разложим аргумент логарифма на множители:</p>"
    html += line(sp.latex(a.arguments[0].value) + "=" + grouped)
    html += line(
        sp.latex(a.arguments[0].value)
        + "="
        + sp.latex(sp.Mul(square, residual, evaluate=False))
    )
    html += "<p>Второе основание является квадратом первого. Перейдём к первому основанию и разделим логарифм произведения: общий квадрат положителен при ненулевом множителе. При вычитании одинаковых логарифмов сохраняем это ограничение:</p>"
    common = logarithm(a.base, sp.latex(square))
    residual_log = logarithm(a.base, sp.latex(residual))
    html += line(common + "+" + residual_log + r"\le" + common)
    html += system(a, factor, residual_log + r"\le0")
    html += (
        "<p>Основание меньше единицы, поэтому знак сравнения аргументов меняется:</p>"
    )
    html += system(a, factor, sp.latex(residual) + r"\ge1")
    bound = sp.solve(residual - 1, X)[0]
    html += system(a, factor, r"x\ge" + sp.latex(bound))
    return html + line(alternatives("x", a.solution))


def render_three_methods(a):
    factor, residual, zero = shape(a, 2)
    if not (
        a.base > 1
        and a.atoms[1].base ** 2 == a.base
        and a.coefficients == (1, -sp.Rational(1, 2))
        and a.operator == ">="
    ):
        raise UnsupportedCondition(
            "the reviewed increasing square-factor comparison is required"
        )
    scale = a.base**a.constant
    square = sp.Pow(factor, 2, evaluate=False)
    product = sp.Mul(scale, square, residual, evaluate=False)
    simple = sp.Mul(scale, residual, evaluate=False)
    bound = sp.solve(residual - 1 / scale, X)[0]
    if (
        comparison(scale * residual - 1, ">=").solution - sp.FiniteSet(zero)
        != a.solution
    ):
        raise UnsupportedCondition(
            "the shortened systems must imply the original positive residual domain"
        )
    original = (
        logarithm(a.base, sp.latex(product))
        + r"\ge"
        + logarithm(a.base, sp.latex(square))
    )
    html = "<p>Область определения задаётся положительностью остаточного множителя и ненулевым общим множителем:</p>"
    html += system(a, factor, sp.latex(residual) + ">0") + line(
        alternatives("x", a.domain)
    )
    html += "<p>Первый способ. Приведём логарифмы к первому основанию и внесём числовое слагаемое под логарифм:</p>"
    html += line(original)
    html += line(sp.latex(product) + r"\ge" + sp.latex(square))
    html += "<p>На исходной области общий квадрат положителен. Сократим его и учтём ОДЗ:</p>"
    html += line(sp.latex(simple) + r"\ge1")
    html += line(sp.latex(residual) + r"\ge" + sp.latex(1 / scale))
    html += line(alternatives("x", a.solution))
    html += "<p>Другой способ. Запишем сразу равносильную систему. Положительная правая часть сравнения обеспечивает положительность оставшегося аргумента:</p>"
    html += line(original)
    html += line(
        r"\begin{cases}"
        + sp.latex(product)
        + r"\ge"
        + sp.latex(square)
        + r"\\"
        + sp.latex(square)
        + r">0\end{cases}"
    )
    html += system(a, factor, sp.latex(simple) + r"\ge1")
    html += system(a, factor, r"x\ge" + sp.latex(bound))
    html += line(alternatives("x", a.solution))
    html += "<p>Ещё один способ. Разделим логарифм произведения и вычтем одинаковые слагаемые, сохранив область определения исчезающего логарифма:</p>"
    common = logarithm(a.base, sp.latex(square))
    residual_log = logarithm(a.base, sp.latex(residual))
    html += line(
        sum_terms([(1, common), (1, residual_log), (a.constant, "")]) + r"\ge" + common
    )
    html += system(a, factor, residual_log + r"\ge" + sp.latex(-a.constant))
    html += system(a, factor, sp.latex(residual) + r"\ge" + sp.latex(1 / scale))
    html += system(a, factor, r"x\ge" + sp.latex(bound))
    return html + line(alternatives("x", a.solution))
