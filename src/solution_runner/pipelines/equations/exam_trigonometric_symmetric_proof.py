"""Keep the substitution proof and the parent's independent sign proof."""

import sympy as sp

from ..probability.common import line
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_symmetric import V


def proof(a):
    if a.symmetric.nonpositive:
        return nonpositive(a)
    from .exam_trigonometric_proof import families, formula, polynomial

    name = a.symmetric.variable
    t = sp.Symbol(name, real=True)
    html = line(a.original)
    html += (
        "<p>Применим формулу суммы кубов и основное тригонометрическое тождество:</p>"
    )
    html += line(
        formula(S**3 + C**3) + "=" + formula((S + C) * (S * S - S * C + C * C))
    )
    html += line(formula(S * S + C * C) + "=1")
    html += line(formula(S**3 + C**3) + "=" + formula((S + C) * (1 - S * C)))
    html += "<p>Введём обозначение и выразим произведение через квадрат суммы:</p>"
    html += line(name + "=" + formula(S + C))
    html += line(formula((S + C) ** 2) + "=1+2" + formula(S * C))
    html += line(formula(S * C) + "=" + sp.latex((t * t - 1) / 2))
    html += line(sp.latex(a.symmetric.polynomial.subs(V, t)) + "=0")
    html += line(sp.latex(sp.factor(a.symmetric.polynomial.subs(V, t))) + "=0")
    html += "<p>Область возможных значений суммы следует из основного тождества:</p>"
    html += line(formula((S + C) ** 2) + "=2-" + formula((S - C) ** 2) + r"\le2")
    html += line(r"-\sqrt2\le " + name + r"\le\sqrt2")
    for value in roots(a.symmetric.polynomial.subs(V, X)):
        html += line(name + "=" + sp.latex(value))
    for b in sorted(a.branches, key=lambda b: not b.impossible):
        if b.impossible:
            html += "<p>Это значение суммы находится вне её области возможных значений и исключается:</p>"
            html += line(formula(b.original) + "=0")
        else:
            html += "<p>Вернёмся к исходной переменной:</p>"
            html += polynomial(b)
    html += "<p>Запишем полученные серии, учитывая произвольность целого параметра:</p>"
    for family in families(a):
        html += line(family + r",\quad k\in\mathbb Z")
    return "<p>Решим уравнение с помощью замены суммы синуса и косинуса:</p>", html


def nonpositive(a):
    from .exam_trigonometric_proof import families, formula

    html = line(a.original)
    html += line(formula(S * S + C * C) + "=1")
    html += line(formula(S * S * (S - 1) + C * C * (C - 1)) + "=0")
    html += "<p>Каждое слагаемое неположительно:</p>"
    html += line(r"-1\le\sin x\le1,\quad-1\le\cos x\le1")
    html += line(formula(S - 1) + r"\le0,\quad " + formula(C - 1) + r"\le0")
    html += line(formula(S * S) + r"\ge0,\quad " + formula(C * C) + r"\ge0")
    html += line(
        formula(S * S * (S - 1)) + r"\le0,\quad " + formula(C * C * (C - 1)) + r"\le0"
    )
    html += "<p>Сумма двух неположительных слагаемых равна нулю, только когда каждое равно нулю:</p>"
    html += line(
        formula(S * S * (S - 1)) + r"=0,\quad " + formula(C * C * (C - 1)) + "=0"
    )
    html += line(formula(S) + r"\in\{0;1\},\quad " + formula(C) + r"\in\{0;1\}")
    html += "<p>Основное тождество оставляет две пары значений:</p>"
    html += line(formula(S * S + C * C) + "=1")
    html += line(r"(\sin x;\cos x)\in\{(0;1);(1;0)\}")
    for family in families(a):
        html += line(family + r",\quad k\in\mathbb Z")
    return "<p>Сохраним независимое решение с помощью знаков слагаемых:</p>", html
