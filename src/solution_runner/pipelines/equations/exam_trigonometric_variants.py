"""Explain scaled angles, reciprocal substitutions and the parent's second method."""

import re

import sympy as sp

from ..probability.common import line
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_compile import C, S, T, U


def argument(scale):
    return sp.latex(scale * sp.Symbol("x", real=True))


def proof(a):
    from .exam_trigonometric_proof import candidate_lines, formula, polynomial

    theta = argument(a.scale)
    if a.reciprocal is not None:
        return reciprocal(a)
    intro = "<p>Используем формулы приведения и решим уравнение относительно тригонометрической функции:</p>"
    html = ""
    if a.power_angle is not None and a.preferred == S and a.scale == 2 * a.power_angle:
        from .exam_trigonometric_sixth_proof import proof as sixth_proof

        return sixth_proof(a)
    if a.rewritten is not None:
        html += "<p>Свернём произведения и разность квадратов по тригонометрическим тождествам:</p>"
        html += line(sp.latex(a.rewritten) + "=0")
    if a.doubled:
        intro, reduced = power_reduction(a, theta)
        html += reduced
    else:
        for text, value in a.identities:
            html += line(text + "=" + formula(value, theta))
        html += line(formula(a.raw, theta) + "=0")
        if a.raw != a.reduced:
            other = S if a.preferred == C else C
            html += line(
                formula(other**2, theta) + "=" + formula(1 - a.preferred**2, theta)
            )
            html += line(formula(a.reduced, theta) + "=0")
    if a.factorization and len(a.branches) > 1:
        html += "<p>Вынесем общий множитель и приравняем каждый множитель к нулю:</p>"
        html += line(formula(sp.factor(a.reduced, extension=True), theta) + "=0")
    for branch in a.branches:
        if a.division:
            from .exam_trigonometric_division import proof as divide

            if len(a.branches) != 1:
                from ..word_problems.common import UnsupportedCondition

                raise UnsupportedCondition(
                    "one polynomial factor is required for guarded division"
                )
            html += divide(branch, theta, a.scale)
            continue
        p = sp.Poly(branch.polynomial, branch.variable)
        if (
            p.degree() == 4
            and not a.factorization
            and all(power[0] % 2 == 0 for power in p.monoms())
        ):
            u = sp.Symbol("u", real=True)
            quadratic = sum(coef * u ** (power[0] // 2) for power, coef in p.terms())
            html += "<p>Решим квадратное уравнение относительно квадрата функции:</p>"
            html += line(
                "u=" + formula(branch.variable**2, theta) + r",\quad0\le u\le1"
            )
            html += line(sp.latex(quadratic) + "=0")
            for value in roots(quadratic.subs(u, X)):
                html += line("u=" + sp.latex(value))
                if 0 <= value <= 1:
                    html += line(
                        formula(branch.variable**2, theta) + "=" + sp.latex(value)
                    )
                    html += line(
                        formula(branch.variable, theta)
                        + r"=\pm"
                        + sp.latex(sp.sqrt(value))
                    )
            html += candidate_lines(
                branch, angle=theta, root_scale=a.scale, allow_inverse=a.allow_inverse
            )
            continue
        html += polynomial(
            branch,
            angle=theta,
            root_scale=a.scale,
            allow_inverse=a.allow_inverse,
            factorization=a.factorization,
        )
    if a.scale != 1:
        html += (
            "<p>При возвращении к x делим углы и периоды каждой серии на "
            + str(a.scale)
            + ".</p>"
        )
    if a.merged:
        from .exam_trigonometric_proof import families

        html += "<p>Объединим полученные серии в одну арифметическую прогрессию:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return intro, html


def power_reduction(a, theta):
    from .exam_trigonometric_proof import formula

    half = argument(a.scale / 2)
    if a.division:
        intro = "<p>Применим формулу приведения и косинуса двойного угла:</p>"
        intro += line(r"\cos(" + theta + r")=1-2\sin^2(" + half + ")")
    else:
        intro = "<p>Воспользуемся формулой понижения степени:</p>"
        intro += line(r"\sin^2(" + half + r")=\frac{1-\cos(" + theta + ")}{2}")
        intro += line(
            r"\sin^4("
            + half
            + r")=\frac{1}{4}(\cos^2("
            + theta
            + r")-2\cos("
            + theta
            + ")+1)"
        )
    return intro, line(formula(a.raw, theta) + "=0")


def reciprocal(a):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import formula, series_lines

    variable = a.branches[0].variable
    t = sp.Symbol("t", real=True)
    name = a.substitution or "t"
    angle = argument(a.scale)
    html = "<p>Знаменатели исходного уравнения не должны обращаться в нуль:</p>"
    if variable in (T, U):
        for pole in a.poles:
            html += line(formula(pole, angle) + r"\ne0")
    html += line(formula(variable, angle) + r"\ne0")
    for text, value in a.identities:
        html += line(text + "=" + formula(value, angle))
    html += "<p>Введём обозначение:</p>" + line(
        name + "=" + formula(1 / variable, angle) + r",\quad " + name + r"\ne0"
    )
    html += line(sp.latex(a.reciprocal, symbol_names={t: name}) + "=0")
    A, B, C0 = sp.Poly(a.reciprocal, t).all_coeffs()
    html += line("D=" + sp.latex(sp.simplify(B * B - 4 * A * C0)))
    for value in roots(a.reciprocal.subs(t, X)):
        html += line(name + "=" + sp.latex(value))
        if value == 0:
            html += "<p>Нулевая величина невозможна для обратной функции.</p>"
            continue
        back = sp.simplify(1 / value)
        html += "<p>Вернёмся к исходной переменной:</p>" + line(
            formula(variable, angle) + "=" + sp.latex(back)
        )
        if back not in a.branches[0].values:
            html += (
                "<p>Это значение нарушает исходную область определения.</p>"
                if variable in (T, U)
                else "<p>Это значение не входит в отрезок от −1 до 1, поэтому корней нет.</p>"
            )
        else:
            for text in series_lines(
                tuple(
                    (q / a.scale, p / a.scale)
                    for q, p in level_series(variable, back, a.allow_inverse)
                ),
                sine_inverse=a.sine_inverse,
            ):
                html += line(text + r",\quad k\in\mathbb Z")
    return (
        "<p>Сведём уравнение к квадратному заменой обратной тригонометрической функции:</p>",
        html,
    )


def method_notes(a):
    from .exam_trigonometric_proof import first

    html = ""
    if a.triple_angle is not None and a.triple_angle.note:
        from .exam_trigonometric_triple_angle import note

        html += note(a)
    if a.alternative is not None:
        alternative_intro, alternative_steps = first(a.alternative)
        html += (
            (
                "<p><b>Приведём другое решение.</b></p>"
                if a.single_part
                else "<p><b>Приведём другое решение пункта а).</b></p>"
            )
            + alternative_intro
            + alternative_steps
        )
    return html


def selection_notes(a, system_image=""):
    from .exam_trigonometric_proof import inequality_selection

    html = ""
    if a.selection_note:
        html += (
            "<p><b>Примечание.</b> Пункт б) можно решить при помощи двойных неравенств.</p>"
            + inequality_selection(a)
        )
    if a.circle_note:
        html += "<p><b>Примечание.</b> Отобрать корни можно, используя тригонометрическую окружность (см. рис.).</p>"
    if a.auxiliary_notes:
        from .exam_trigonometric_auxiliary_notes import notes

        html += notes(a, system_image)
    if a.angle_product is not None and a.angle_product.note:
        from .exam_trigonometric_angle_domain import note

        html += note(a)
    return html


def root_notation(a, rendered):
    from .exam_trigonometric_proof import series_lines

    pairs = tuple(zip(getattr(a, "series", ()), getattr(a, "family_parameters", ())))
    restricted = getattr(a, "restricted_families", ())
    if restricted:
        pairs = tuple(((f.offset, f.period), f.parameter) for f in restricted)
    for item, name in pairs:
        if name != "k":
            for text in series_lines((item,), sine_inverse=a.sine_inverse):
                old = text + r",\quad k\in\mathbb Z"
                new = text.replace("k", name) + r",\quad " + name + r"\in\mathbb Z"
                rendered = tuple(value.replace(old, new) for value in rendered)
    if a.parameter == "k":
        return rendered
    return tuple(
        re.sub(r"(?<![A-Za-z_-])k(?![A-Za-z_-])", a.parameter, text)
        for text in rendered
    )
