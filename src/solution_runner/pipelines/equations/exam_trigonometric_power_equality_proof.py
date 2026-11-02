"""Keep positive-factor cancellation before the parent's trigonometric algebra."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def power(base, exponent):
    from .exam_trigonometric_proof import formula

    if exponent == 0:
        return "1"
    return r"\left(" + sp.latex(base) + r"\right)^{" + formula(exponent) + "}"


def product(primes):
    return r"\cdot".join(power(p, e) for p, e in primes if e != 0) or "1"


def exponent_steps(a, left, right):
    from .exam_trigonometric_proof import formula

    data = a.power_equality
    if data.equal_powers is not None:
        base, first, second = data.equal_powers
        html = line(power(base, first) + "=" + power(base, second))
        html += line(sp.latex(base) + r">0,\quad " + sp.latex(base) + r"\ne1")
        html += "<p>У положительных степеней с одинаковым основанием, отличным от единицы, равны показатели:</p>"
        return html + line(formula(first) + "=" + formula(second))
    target = power(data.base, data.exponent) + "=1"
    html = ""
    if target != product(left.items()) + "=" + product(right.items()):
        html += "<p>Разделим положительные степени и объединим множители с общим показателем:</p>"
        html += line(target)
    html += line(sp.latex(data.base) + r">0,\quad " + sp.latex(data.base) + r"\ne1")
    return (
        html
        + "<p>Степень с таким основанием равна единице только при нулевом показателе:</p>"
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    data = a.power_equality
    html = ""
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    html += line(formula(data.left) + "=" + formula(data.right))
    html += (
        "<p>Разложим основания на простые множители и применим свойства степеней:</p>"
    )
    html += line(product(data.left_primes) + "=" + product(data.right_primes))
    left, right = dict(data.left_primes), dict(data.right_primes)
    shared = tuple((p, e) for p, e in data.left_primes if e != 0 and e == right.get(p))
    if shared:
        html += "<p>Разделим обе части на общий положительный множитель:</p>"
        html += line(product(shared) + ">0")
        for p, _ in shared:
            left.pop(p)
            right.pop(p)
        html += line(product(left.items()) + "=" + product(right.items()))
    html += exponent_steps(a, left, right)
    if a.homogeneous is not None:
        from .exam_trigonometric_homogeneous_proof import proof as homogeneous

        html += homogeneous(replace(a, identities=()))[1]
    else:
        if a.scale != 1:
            name = "sin" if a.preferred == S else "cos"
            identity = 2 * S * C if a.preferred == S else C * C - S * S
            html += line(formula(data.exponent) + "=0")
            html += "<p>Применим формулу двойного угла:</p>"
            html += line("\\" + name + "2x=" + formula(identity))
        if len(a.branches) > 1:
            html += line(formula(sp.factor(data.exponent, extension=True)) + "=0")
        for branch in a.branches:
            html += polynomial(
                branch,
                allow_inverse=a.allow_inverse,
                factorization=True,
                angle="x" if a.scale == 1 else sp.latex(a.scale) + "x",
                root_scale=a.scale,
            )
    return "<p>Применим формулы приведения и преобразуем исходное уравнение:</p>", html
