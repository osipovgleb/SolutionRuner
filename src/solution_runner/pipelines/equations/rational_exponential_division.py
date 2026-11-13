"""Parent division and cancellation steps over the shared substitution solution."""

from dataclasses import replace
from functools import partial

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .logarithm_parser import Node
from .rational_exponential_proof import common_fraction, named_normalized
from .rational_exponential_proof import render as substitution_proof
from .rational_inequality_division_methods import difference, pipeline, step
from .rational_inequality_methods import (
    Step,
    divide_affine_fractions,
    divisions,
    fraction,
)
from .rational_inequality_parser import RationalParser, X, polynomial
from .rational_inequality_polynomial_methods import collect
from .rational_inequality_proof import RELATION, interval_signs_text
from .rational_inequality_roots import ordered


def append_common(stage, steps, whole, values):
    residual = step(whole, values)
    synthetic = replace(
        stage,
        left=RationalParser(residual.text).parse(),
        right=Node(sp.Integer(0), "0"),
    )
    n, d = common_fraction(synthetic)
    return [
        *steps,
        residual,
        Step(fraction(n, d), stage.original),
        Step(fraction(sp.expand(n), d), stage.original),
    ]


def divided(stage):
    identities, quotients, remainders = divide_affine_fractions(divisions(stage.left))
    whole = sp.expand(sum(quotients) - stage.right.value)
    if polynomial(whole).degree() > 0:
        raise UnsupportedCondition(
            "the affine polynomial parts must cancel, leaving at most a constant"
        )
    residual = sp.Add(whole, *remainders, evaluate=False)
    last = Step(sp.latex(residual), stage.original)
    steps = [last]
    synthetic = replace(
        stage, left=RationalParser(last.text).parse(), right=Node(sp.Integer(0), "0")
    )
    n, d = common_fraction(synthetic)
    return identities, [
        *steps,
        Step(fraction(n, d), stage.original),
        Step(fraction(sp.expand(n), d), stage.original),
    ]


def cubic_division(stage):
    whole, lf = collect(stage.left)
    right, rf = collect(stage.right)
    if (
        whole != 0
        or len(lf) != 1
        or len(rf) != 2
        or polynomial(lf[0][0]).degree() != 3
        or polynomial(lf[0][1]).degree() != 2
        or polynomial(right).degree() != 1
        or any(polynomial(n).degree() > 0 or polynomial(d).degree() != 1 for n, d in rf)
    ):
        raise UnsupportedCondition(
            "the reviewed cubic division needs one cubic fraction and an affine bound with two reciprocal terms"
        )
    n, d = lf[0]
    q, r = sp.div(n, d, X)
    if sp.expand(q - right) != 0:
        raise UnsupportedCondition(
            "the extracted cubic quotient must cancel the whole right side"
        )
    identity = (
        sp.latex(n)
        + "="
        + sp.latex(sp.Add(sp.Mul(q, d, evaluate=False), r, evaluate=False)),
        n,
        q * d + r,
    )
    _, steps = pipeline(stage)
    return [identity], steps


def cancelled(stage):
    whole, values = difference(stage)
    if polynomial(whole).degree() != 1 or len(values) != 2 or len(stage.holes) != 1:
        raise UnsupportedCondition(
            "the contained cancellation needs an affine whole part and two fractions with one original hole"
        )
    values = sorted(values, key=lambda pair: polynomial(pair[1]).degree())
    (m, e), (n, d) = values
    factor = sp.cancel(d / e)
    if (
        polynomial(e).degree() != 1
        or polynomial(d).degree() != 2
        or not factor.is_polynomial(X)
        or polynomial(factor).degree() != 1
    ):
        raise UnsupportedCondition(
            "one affine denominator must divide the quadratic denominator"
        )
    combined = sp.expand(n + m * factor)
    factored = sp.factor(combined)
    rows = [
        step(
            whole,
            [
                (
                    sp.Add(n, sp.Mul(m, factor, evaluate=False), evaluate=False),
                    sp.factor(d),
                )
            ],
        ),
        step(whole, [(combined, sp.factor(d))]),
        step(whole, [(factored, sp.factor(d))]),
    ]
    reduced_n, reduced_d = sp.fraction(sp.cancel(combined / d))
    if polynomial(sp.gcd(combined, d)).degree() != 1:
        raise UnsupportedCondition(
            "the exact affine factor must cancel once while retaining its original exclusion"
        )
    return [], append_common(stage, rows, whole, [(reduced_n, reduced_d)])


def cube_grouping(stage):
    n, d = common_fraction(stage)
    p = polynomial(sp.expand(n))
    if len(stage.holes) != 1 or p.degree() != 3 or p.LC() != 1:
        return None
    h = stage.holes[0]
    k = p.nth(2)
    if p.nth(0) != -(h**3) or sp.expand(n - (X**3 - h**3) - k * X * (X - h)) != 0:
        return None
    first = sp.Add(X**3 - h**3, k * X * (X - h), evaluate=False)
    second = sp.Add(
        sp.Mul(X - h, X**2 + h * X + h**2, evaluate=False),
        k * X * (X - h),
        evaluate=False,
    )
    q = sp.expand(X**2 + (h + k) * X + h**2)
    values = [
        n,
        sp.expand(n),
        first,
        second,
        sp.Mul(X - h, q, evaluate=False),
        sp.Mul(X - h, sp.factor(q), evaluate=False),
    ]
    return [Step(fraction(v, d), stage.original) for v in values]


def roots(stage, variable):
    p = polynomial(sp.fraction(stage.expression)[0])
    if p.degree() != 2 or all(r.is_Rational for r in stage.zeros):
        return ""
    A, B, C = p.all_coeffs()
    discriminant = sp.expand(B * B - 4 * A * C)
    fmt = lambda value: sp.latex(value).replace("x", variable)
    html = "<p>Найдём корни квадратного числителя по дискриминанту:</p>"
    html += line(fmt(p.as_expr()) + "=0")
    html += line(
        "D=("
        + sp.latex(B)
        + ")^2-4\\cdot("
        + sp.latex(A)
        + ")\\cdot("
        + sp.latex(C)
        + ")="
        + sp.latex(discriminant)
    )
    html += line(
        variable
        + r"=\frac{-("
        + sp.latex(B)
        + r")\pm\sqrt{"
        + sp.latex(discriminant)
        + r"}}{2\cdot("
        + sp.latex(A)
        + ")}"
    )
    html += line(r",\quad ".join(variable + "=" + fmt(r) for r in stage.zeros))
    html += "<p>Расположим корни и исключённые точки в точном порядке, учитывая положительность замены:</p>"
    return html + line(
        "<".join(fmt(v) for v in ordered(set(stage.points) | {sp.Integer(0)}))
    )


METHODS = {
    "affine_division": divided,
    "contained_cancellation": cancelled,
    "cubic_division": cubic_division,
}


def algebra(a, variable, *, method):
    stage = a.stage
    if method == "cube_grouping":
        identities = []
        steps = cube_grouping(stage)
        if steps is None:
            raise UnsupportedCondition(
                "the second grouping requires an exact difference of cubes"
            )
        html = "<p>Приведём к общему знаменателю. Выделим разность кубов и затем общий множитель:</p>"
    else:
        identities, steps = METHODS[method](stage)
        html = (
            "<p>Выделим целые части делением многочленов:</p>"
            if identities
            else "<p>Объединим дроби с вложенными знаменателями и вынесем общий множитель:</p>"
        )
    for text, left, right in identities:
        if sp.expand(left - right) != 0:
            raise UnsupportedCondition("each displayed division identity must be exact")
        html += line(text.replace("x", variable))
    previous = None
    for item in steps:
        if sp.cancel(item.value - stage.original) != 0:
            raise UnsupportedCondition(
                "each algebraic step must preserve the original difference"
            )
        if item.text != previous:
            html += line(item.text.replace("x", variable) + RELATION[a.operator] + "0")
            previous = item.text
    if stage.holes:
        html += "<p>Сокращение множителя не возвращает исключённую точку в область определения:</p>"
        html += line(
            r",\quad ".join(variable + r"\ne " + sp.latex(p) for p in stage.holes)
        )
    html += named_normalized(stage, variable) + roots(stage, variable)
    html += "<p>Решаем методом интервалов, не включая исходные полюсы и сокращённые исключения:</p>"
    html += line(interval_signs_text(stage).replace("x", variable))
    return html + line(alternatives(variable, stage.solution))


def render(a, variable, image="", *, method):
    if method == "contained_cancellation" and cube_grouping(a.stage) is not None:
        first = substitution_proof(
            a, variable, image, algebra_builder=partial(algebra, method="cube_grouping")
        )
        second = substitution_proof(
            a, variable, algebra_builder=partial(algebra, method=method)
        )
        return (
            "<p><strong>Первый способ.</strong></p>"
            + first
            + "<p><strong>Второй способ.</strong></p>"
            + second
        )
    return substitution_proof(
        a, variable, image, algebra_builder=partial(algebra, method=method)
    )
