"""Explain the original domain, equivalent square and rejected trigonometric roots."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_inverse import angles, compare_q, turn
from .exam_trigonometric_proof import families, formula, series_lines


def nominal(variable, value):
    if value == 0:
        return ((sp.S.Zero if variable == S else sp.S.Half, sp.S.One),)
    if variable == S:
        alpha = sp.S.Half - sp.acos(value) / sp.pi
        return tuple(
            dict.fromkeys(
                (q - 2 if compare_q(q, sp.S.One) > 0 else q, sp.Integer(2))
                for q in (alpha, 1 - alpha)
            )
        )
    alpha = sp.acos(value) / sp.pi
    return tuple(dict.fromkeys((q, sp.Integer(2)) for q in (alpha, -alpha)))


def parameter(a, q, *, zero=False):
    roles = a.radical_equation.parameters
    if not roles:
        return "k"
    if zero:
        return roles[0]
    return roles[1] if turn(q) in a.residues else roles[2]


def sign_condition(a, right):
    if len(right.free_symbols) != 1:
        return formula(right) + r"\ge0"
    variable = next(iter(right.free_symbols))
    coefficient = sp.expand(right).coeff(variable)
    boundary = sp.simplify(-right.subs(variable, 0) / coefficient)
    strict = boundary == 0 and variable in a.poles
    relation = (
        (">" if strict else r"\ge") if coefficient > 0 else ("<" if strict else r"\le")
    )
    return formula(variable) + relation + " " + sp.latex(boundary)


def checked_values(a, q):
    substitutions = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
    data = a.radical_equation
    radicand = sp.simplify(data.radicand.subs(substitutions))
    right = sp.simplify((data.right / data.multiplier).subs(substitutions))
    poles = tuple(sp.simplify(p.subs(substitutions)) for p in a.poles)
    accepted = (
        all(v != 0 for v in poles)
        and compare(radicand, sp.S.Zero) >= 0
        and compare(right, sp.S.Zero) >= 0
    )
    return radicand, right, poles, accepted


def candidates(a, branch):
    html = ""
    values = sorted(branch.candidates, key=lambda v: (v != 0, abs(v) != 1))
    if a.sine_inverse:
        values = sorted(values, key=cmp_to_key(compare))
    for value in values:
        html += line(formula(branch.variable) + "=" + sp.latex(value))
        if compare(value, -sp.S.One) < 0 or compare(value, sp.S.One) > 0:
            html += "<p>Значение вне отрезка от −1 до 1, поэтому эта ветвь не имеет корней.</p>"
            continue
        checks = tuple(
            (q, checked_values(a, q)) for q in angles(branch.variable, value, True)
        )
        if not any(row[-1] for _, row in checks):
            html += "<p>Эта ветвь нарушает исходное ограничение:</p>"
            for _q, (rad, right, poles, _) in checks:
                if any(v == 0 for v in poles):
                    html += line(r"\text{исходный знаменатель}=0")
                elif compare(right, sp.S.Zero) < 0:
                    html += line(r"\text{правая часть}=" + sp.latex(right) + "<0")
                else:
                    html += line(
                        r"\text{подкоренное выражение}=" + sp.latex(rad) + "<0"
                    )
            continue
        for q, p in nominal(branch.variable, value):
            name = parameter(a, q, zero=value == 0 and branch.variable == S)
            for text in series_lines(((q, p),), sine_inverse=a.sine_inverse):
                html += line(
                    text.replace("k", name) + r",\quad " + name + r"\in\mathbb Z"
                )
        html += "<p>Проверим знак и область определения; значения функций повторяются через 2π:</p>"
        for q, (rad, right, poles, accepted) in checks:
            q = q - 2 if compare_q(q, sp.S.One) > 0 else q
            name = parameter(a, q, zero=value == 0 and branch.variable == S)
            text = series_lines(((q, sp.Integer(2)),), sine_inverse=a.sine_inverse)[
                0
            ].replace("k", name)
            text += (
                r"\quad\Rightarrow\quad\text{подкоренное выражение}="
                + sp.latex(rad)
                + r",\quad\text{правая часть}="
                + sp.latex(right)
            )
            if poles:
                text += r",\quad\text{знаменатель}=" + ";".join(
                    sp.latex(v) for v in poles
                )
            html += line(text)
            html += (
                "<p>Серия удовлетворяет исходному уравнению.</p>"
                if accepted
                else "<p>Серию исключаем по исходным ограничениям.</p>"
            )
    return html


def proof(a):
    data = a.radical_equation
    right = sp.cancel(data.right / data.multiplier)
    html = line(a.original)
    html += "<p>Сохраним область определения исходного уравнения:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(data.radicand) + r"\ge0")
    for text, value in a.identities:
        plain = "".join(c for c in text if c not in " (){}\t\n")
        if plain not in (r"\sinx", r"\cosx"):
            html += line(text + "=" + formula(value))
    html += "<p>Корень неотрицателен. Поэтому правая часть после переноса слагаемых тоже должна быть неотрицательной:</p>"
    html += line(sign_condition(a, right))
    if data.cleared.free_symbols:
        html += "<p>При этом условии исходный знаменатель ненулевой; умножим обе части на него:</p>"
    html += line(r"\sqrt{" + formula(data.radicand) + "}=" + formula(right))
    html += "<p>С учётом этих ограничений возведение в квадрат равносильно. Используем основное тригонометрическое тождество:</p>"
    html += line(formula(data.radicand) + r"=\left(" + formula(right) + r"\right)^2")
    html += line(r"\sin^2x+\cos^2x=1")
    for branch in a.branches:
        polynomial = branch.polynomial
        html += line(formula(polynomial) + "=0")
        factored = sp.factor(polynomial, extension=True)
        if factored != polynomial:
            html += line(formula(factored) + "=0")
        html += candidates(a, branch)
    html += "<p>Оставляем только допустимые серии; параметры в окончательной записи пробегают все целые числа:</p>"
    names = a.family_parameters or ("k",) * len(families(a))
    for text, name in zip(families(a), names):
        html += line(text + r",\quad " + name + r"\in\mathbb Z")
    return (
        "<p>Преобразуем уравнение, сохраняя знак корня и исходную область определения:</p>",
        html,
    )
