"""Explain the original domain, equivalent square and rejected trigonometric roots."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_inverse import angles, compare_q, level_series, turn
from .exam_trigonometric_proof import families, formula, series_lines


def nominal(variable, value):
    if variable in (T, U):
        return tuple(
            (q - 1 if compare_q(q, sp.S.Half) > 0 else q, p)
            for q, p in level_series(variable, value)
        )
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
    strict = boundary == 0 and (
        variable in a.poles or variable in a.radical_equation.positive_arguments
    )
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
        and all(compare(v, sp.S.Zero) > 0 for v in positive_values(a, q))
        and compare(radicand, sp.S.Zero) >= 0
        and compare(right, sp.S.Zero) >= 0
    )
    return radicand, right, poles, accepted


def positive_values(a, q):
    return tuple(
        sp.simplify(argument.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
        for argument in a.radical_equation.positive_arguments
    )


def rejection(a, q, radicand, right, poles):
    if any(v == 0 for v in poles):
        return line(r"\text{исходный знаменатель}=0")
    invalid = [v for v in positive_values(a, q) if compare(v, sp.S.Zero) <= 0]
    if invalid:
        return line(r"\text{аргумент логарифма}=" + sp.latex(invalid[0]) + r"\le0")
    if compare(right, sp.S.Zero) < 0:
        return line(r"\text{правая часть}=" + sp.latex(right) + "<0")
    return line(r"\text{подкоренное выражение}=" + sp.latex(radicand) + "<0")


def candidates(a, branch):
    html = ""
    values = sorted(branch.candidates, key=lambda v: (v != 0, abs(v) != 1))
    if a.sine_inverse:
        values = sorted(values, key=cmp_to_key(compare))
    for value in values:
        html += line(formula(branch.variable) + "=" + sp.latex(value))
        if branch.variable in (S, C) and (
            compare(value, -sp.S.One) < 0 or compare(value, sp.S.One) > 0
        ):
            html += "<p>Значение вне отрезка от −1 до 1, поэтому эта ветвь не имеет корней.</p>"
            continue
        checks = tuple(
            (q, checked_values(a, q)) for q in angles(branch.variable, value, True)
        )
        if not any(row[-1] for _, row in checks):
            html += "<p>Эта ветвь нарушает исходное ограничение:</p>"
            for q, (rad, right, poles, _) in checks:
                html += rejection(a, q, rad, right, poles)
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
            arguments = positive_values(a, q)
            if arguments:
                text += r",\quad\text{аргумент логарифма}=" + ";".join(
                    sp.latex(v) for v in arguments
                )
            html += line(text)
            html += (
                "<p>Серия удовлетворяет исходному уравнению.</p>"
                if accepted
                else "<p>Серию исключаем по исходным ограничениям.</p>"
            )
    return html


def proof(a):
    if a.radical_equation.auxiliary_branch is not None:
        return double_proof(a)
    data = a.radical_equation
    right = sp.cancel(data.right / data.multiplier)
    html = line(a.original)
    html += "<p>Сохраним область определения исходного уравнения:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(data.radicand) + r"\ge0")
    if data.inverse_identity is not None:
        base, argument = data.inverse_identity
        html += line(formula(argument) + ">0")
        if data.radicand == S * C:
            html += line(formula(S if argument == C else C) + r"\ge0")
        html += "<p>При положительном аргументе применим взаимную обратность показательной функции и логарифма:</p>"
        html += line(
            r"\left("
            + sp.latex(base)
            + r"\right)^{\log_{"
            + sp.latex(base)
            + r"}\left("
            + formula(argument)
            + r"\right)}="
            + formula(argument)
        )
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
    if data.mixed_factors:
        html += line(formula(data.squared) + "=0")
        if sp.expand(data.squared - a.raw) != 0:
            html += line(formula(a.raw) + "=0")
        html += line(formula(sp.factor(a.raw, extension=True)) + "=0")
        html += (
            "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
        )
    for branch in a.branches:
        if branch.original is not None and branch.variable in (T, U):
            from .exam_trigonometric_ratios import linear_proof

            html += linear_proof(branch, "x")
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


def double_candidates(a, branch):
    from .exam_trigonometric_safe_square import auxiliary_series

    shifted = sp.latex(2 * sp.Symbol("x", real=True) + branch.angle_shift * sp.pi)
    unit = tuple(
        (q - p if q > p / 2 else q, p)
        for q, p in level_series(branch.variable, branch.values[0])
    )
    html = "<p>Сначала найдём сдвинутый угол, затем выразим исходную переменную:</p>"
    for text in series_lines(unit):
        html += line(shifted + "=" + text.split("=", 1)[1] + r",\quad k\in\mathbb Z")
    nominal = auxiliary_series(branch)
    for text in series_lines(nominal):
        html += line(text + r",\quad k\in\mathbb Z")
    html += (
        "<p>В каждой серии проверим исходные ограничения при чётном и нечётном k:</p>"
    )
    for q, period in nominal:
        for parity in (0, 1):
            actual = q + parity * period
            radicand, right, poles, accepted = checked_values(a, actual)
            html += line(
                "k=2n"
                + ("+1" if parity else "")
                + r":\quad x="
                + sp.latex(actual * sp.pi)
                + r"+2\pi n,\quad\text{правая часть}="
                + sp.latex(right)
            )
            if accepted:
                html += "<p>Серия удовлетворяет исходному уравнению.</p>"
            else:
                html += rejection(a, actual, radicand, right, poles)
                html += "<p>Эту серию исключаем.</p>"
    return html


def double_proof(a):
    from .exam_trigonometric_safe_square import double_polynomial

    data = a.radical_equation
    branch = data.auxiliary_branch
    right = sp.cancel(data.right / data.multiplier)
    radicand = double_polynomial(data.radicand)
    square = double_polynomial(right**2)
    projected = branch.original
    constant = projected.subs({S: 0, C: 0})
    amplitude = sp.sqrt(projected.coeff(S) ** 2 + projected.coeff(C) ** 2)
    shifted = (
        r"\left("
        + sp.latex(2 * sp.Symbol("x", real=True) + branch.angle_shift * sp.pi)
        + r"\right)"
    )
    html = line(a.original)
    if data.multiplier != 1:
        html += "<p>Разделим обе части на ненулевую постоянную перед корнем:</p>"
        html += line(sp.latex(data.multiplier) + r"\ne0")
        html += line(r"\sqrt{" + formula(radicand, "2x") + "}=" + formula(right))
    html += "<p>Учтём область определения и неотрицательность правой части до возведения в квадрат:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(radicand, "2x") + r"\ge0")
    html += sign_condition(a, right)
    html += "<p>При этих ограничениях возведение в квадрат равносильно. Приведём квадрат правой части к двойным углам:</p>"
    html += line(formula(radicand, "2x") + "=(" + formula(right) + ")^2")
    squared = sp.expand(right**2)
    for monomial, identity in (
        (S**2, r"\sin^2x=\frac{1-\cos2x}{2}"),
        (C**2, r"\cos^2x=\frac{1+\cos2x}{2}"),
        (S * C, r"\sin x\cos x=\frac{\sin2x}{2}"),
    ):
        if squared.coeff(monomial):
            html += line(identity)
    html += line(formula(radicand, "2x") + "=" + formula(square, "2x"))
    html += line(formula(projected, "2x") + "=0")
    name = "синуса" if branch.variable == S else "косинуса"
    html += (
        "<p>Разделим на положительную амплитуду и применим формулу "
        + name
        + " суммы:</p>"
    )
    html += line(sp.latex(amplitude) + ">0")
    html += line(
        formula(sp.expand((projected - constant) / amplitude), "2x")
        + "="
        + sp.latex(branch.values[0])
    )
    html += line(formula(branch.variable, shifted) + "=" + sp.latex(branch.values[0]))
    html += double_candidates(a, branch)
    html += "<p>Объединим допустимые серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Решим уравнение с помощью вспомогательного двойного угла.</p>", html
