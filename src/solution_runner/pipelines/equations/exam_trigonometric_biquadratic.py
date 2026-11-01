"""Retain the parent's quadratic equation in the square of one function."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S


def prepare(a, html):
    from .exam_trigonometric_ratio_square import reviewed

    if (
        a.scale != 1
        or not a.strict_domain
        or a.poles
        or a.reduced.free_symbols not in ({S}, {C})
    ):
        return a
    variable = next(iter(a.reduced.free_symbols))
    polynomial = sp.Poly(a.reduced, variable)
    if (
        a.domain.free_symbols != {variable}
        or polynomial.degree() != 4
        or any(power[0] % 2 for power in polynomial.monoms())
        or reviewed(html) != variable
    ):
        return a
    if sp.rem(a.raw - a.reduced, S * S + C * C - 1, S) != 0:
        raise UnsupportedCondition(
            "the biquadratic projection must preserve the unit-circle equation"
        )
    return replace(
        a,
        centered_power=(
            variable,
            sp.S.Zero,
            a.reduced.coeff(variable, 4),
            a.reduced.coeff(variable, 2),
            False,
        ),
    )


def proof(a):
    from .exam_exponential import X
    from .exam_logarithmic_algebra import roots
    from .exam_scalar import compare
    from .exam_trigonometric import Branch
    from .exam_trigonometric_proof import families, formula, polynomial

    variable, _, leading, second, _ = a.centered_power
    u = sp.Symbol("u", real=True)
    q = leading * u * u + second * u + a.reduced.subs(variable, 0)
    levels = roots(q.subs(u, X))
    if not levels:
        raise UnsupportedCondition(
            "the reviewed biquadratic method requires real square levels"
        )
    html = (
        line(a.original)
        + "<p>Корень в знаменателе должен быть определён и отличен от нуля:</p>"
    )
    html += line(formula(a.domain) + ">0")
    for text, value in a.identities:
        if value in (S, C) and text.replace(" ", "") in (
            r"\sin(x)",
            r"\cos(x)",
            r"\sinx",
            r"\cosx",
        ):
            continue
        html += line(text + "=" + formula(value))
    html += "<p>На исходной области определения числитель должен равняться нулю. Применим основное тригонометрическое тождество:</p>"
    html += line(formula(a.raw) + "=0")
    html += line(r"\sin^2x+\cos^2x=1")
    html += line(formula(a.reduced) + "=0")
    html += "<p>Введём квадрат функции как новую переменную и решим квадратное уравнение:</p>"
    html += line("u=" + formula(variable**2) + r",\quad 0\le u\le1")
    html += line(sp.latex(q) + "=0")
    html += line(sp.latex(sp.factor(q, extension=True)) + "=0")
    for level in levels:
        if compare(level, sp.S.Zero) < 0 or compare(level, sp.S.One) > 0:
            html += line(formula(variable**2) + "=" + sp.latex(level))
            html += "<p>Квадрат синуса или косинуса лежит от 0 до 1; эту ветвь исключаем.</p>"
            continue
        values = tuple(dict.fromkeys((-sp.sqrt(level), sp.sqrt(level))))
        accepted = tuple(
            v
            for v in values
            if compare(sp.simplify(a.domain.subs(variable, v)), sp.S.Zero) > 0
        )
        excluded = tuple(v for v in values if v not in accepted)
        b = Branch(
            variable,
            variable**2 - level,
            values,
            accepted,
            a.residues,
            excluded=excluded,
            square_level=True,
        )
        html += "<p>Вернёмся к функции, сохранив строгое условие на знаменатель:</p>"
        html += polynomial(b, allowed_residues=a.residues)
        for v in excluded:
            html += line(
                formula(a.domain)
                + "="
                + sp.latex(sp.simplify(a.domain.subs(variable, v)))
                + r"\le0"
            )
    html += "<p>После проверки исходной области определения остаются серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Решим биквадратное уравнение с сохранением исходной ОДЗ:</p>", html
