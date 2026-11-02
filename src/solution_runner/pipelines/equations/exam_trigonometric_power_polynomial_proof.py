"""Keep the parent's named or direct quadratic and reject every invalid power."""

from functools import partial

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_power_polynomial_roots import case_branches, display_series
from .exam_trigonometric_power_units import E


def argument(data):
    from .exam_trigonometric_proof import formula

    if data.shape.product:
        return formula(sp.cancel(data.unit.argument / (S * C)) * S * C)
    angle = "x" if data.shape.scale == 1 else str(data.shape.scale) + "x"
    return formula(data.multiplier * data.shape.variable**data.shape.power, angle)


def power_text(data):
    return r"\left(" + sp.latex(data.unit.base) + r"\right)^{" + argument(data) + "}"


def expression(data, value):
    name = data.style.substitution or r"\left(" + power_text(data) + r"\right)"
    return sp.latex(value, symbol_names={E: name})


def domain(a):
    from .exam_trigonometric_log_equality import original_text
    from .exam_trigonometric_proof import formula
    from .power_arithmetic import balanced

    html = ""
    if a.poles or a.domain is not None:
        html = "<p>Сохраним область определения исходного уравнения:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    if a.power_polynomial.log_denominator is not None:
        _, argument = a.power_polynomial.log_denominator
        html += line(a.power_polynomial.wrapper + r"\ne0")
        html += line(formula(argument) + ">0") + line(formula(argument) + r"\ne1")
        html += "<p>Аргумент логарифма должен быть положителен и отличен от единицы. Сам логарифм может быть отрицательным, но не нулевым. При этих условиях дробь равна нулю тогда и только тогда, когда её числитель равен нулю.</p>"
        if argument.is_polynomial(S, C) and len(argument.free_symbols) == 1:
            variable = next(iter(argument.free_symbols))
            if sp.degree(argument, variable) == 1:
                coefficient = argument.coeff(variable)
                html += line(
                    formula(variable)
                    + (">" if coefficient > 0 else "<")
                    + sp.latex(-argument.subs(variable, 0) / coefficient)
                )
        if sp.fraction(argument)[1].free_symbols:
            html += "<p>При исходных ненулевых знаменателях умножим неравенство на положительный квадрат знаменателя:</p>"
            html += line(formula(a.domain) + ">0")
    elif a.domain is not None:
        text, _ = balanced(a.power_polynomial.wrapper, 5)
        html += line(original_text(text) + ">0")
        html += "<p>Подкоренное выражение всего знаменателя должно быть строго положительным.</p>"
    return html


def reduction(a):
    from .exam_trigonometric_proof import formula

    data = a.power_polynomial
    html = domain(a)
    for text, value in a.identities:
        if value in (S, C) or text in (r"\tg(x)", r"\ctg(x)"):
            continue
        if value.is_polynomial(S, C):
            other = C if data.shape.variable == S else S
            value = sp.rem(value, S * S + C * C - 1, other)
        html += line(text + "=" + formula(value))
    if data.unit.divisor != 1:
        html += "<p>Разделим исходное уравнение на положительный показательный множитель:</p>"
        html += line(formula(data.unit.divisor) + ">0")
    if data.style.substitution:
        html += "<p>Сделаем замену переменной:</p>"
        html += line(data.style.substitution + "=" + power_text(data))
        html += line(data.style.substitution + ">0")
    else:
        html += "<p>Применим свойства степеней и решим квадратное уравнение относительно показательного выражения:</p>"
        html += line(power_text(data) + ">0")
    value = sp.apart(data.unit.rational, E)
    constant = sum(v for v in sp.Add.make_args(value) if not v.has(E))
    html += line(expression(data, value - constant) + "=" + sp.latex(-constant))
    html += "<p>Приведём к квадратному уравнению и разложим его на множители:</p>"
    html += line(expression(data, data.unit.polynomial) + "=0")
    html += line(
        expression(data, sp.factor(data.unit.polynomial, extension=True)) + "=0"
    )
    return html


def exclusions(a, raw, accepted):
    from .exam_trigonometric_proof import formula, pi

    html = ""
    for q in sorted(set(raw.residues) - set(accepted.residues)):
        html += line("x=" + pi(q / a.scale))
        values = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        for pole in a.poles:
            if sp.simplify(pole.subs(values)) == 0:
                html += line(formula(pole) + "=0")
        if a.domain is not None:
            html += line(
                formula(a.domain) + "=" + sp.latex(sp.simplify(a.domain.subs(values)))
            )
        html += "<p>Эта ветвь нарушает исходную область определения и исключается.</p>"
    return html


def case(a, value, level):
    from .exam_trigonometric_proof import candidate_lines, formula

    data = a.power_polynomial
    html = line((data.style.substitution or power_text(data)) + "=" + sp.latex(value))
    if level is None:
        return (
            html
            + "<p>Положительная степень не может принимать неположительное значение; эта ветвь корней не имеет.</p>"
        )
    if data.style.substitution:
        html += "<p>Вернёмся к исходной переменной:</p>"
        html += line(power_text(data) + "=" + sp.latex(value))
    html += line(
        power_text(data)
        + "="
        + r"\left("
        + sp.latex(data.unit.base)
        + r"\right)^{"
        + sp.latex(level)
        + "}"
    )
    html += line(argument(data) + "=" + sp.latex(level))
    if data.shape.product:
        html += line(r"2\sin x\cos x=\sin2x")
    angle = "x" if a.scale == 1 else str(a.scale) + "x"
    if data.multiplier != 1:
        html += line(
            formula(data.shape.variable**data.shape.power, angle)
            + "="
            + sp.latex(level / data.multiplier)
        )
    raw = case_branches(a, level, constraints=False, allow_inverse=a.allow_inverse)
    accepted = case_branches(a, level, allow_inverse=a.allow_inverse)
    for original, retained in zip(raw, accepted, strict=True):
        html += candidate_lines(
            retained,
            allow_inverse=a.allow_inverse,
            allowed_residues=retained.residues,
            angle=angle,
            root_scale=a.scale,
            series_transform=partial(display_series, data.shape.variable),
        )
        html += exclusions(a, original, retained)
    return html


def proof(a, image=""):
    html = reduction(a)
    if a.image_position == "after-polynomial":
        data = a.power_polynomial
        for value in data.powers:
            html += line(data.style.substitution + "=" + sp.latex(value))
        html += image
    for value, level in zip(
        a.power_polynomial.powers, a.power_polynomial.levels, strict=True
    ):
        html += case(a, value, level)
    if a.power_polynomial.shape.power == 2 and a.series:
        from .exam_trigonometric_proof import families

        html += "<p>Объединим допустимые серии корней, учитывая периодичность:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Преобразуем исходное уравнение:</p>", html
