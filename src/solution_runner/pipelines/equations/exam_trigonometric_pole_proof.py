"""Explain certified cancellation and original poles before selecting root series."""

import re
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from .exam_trigonometric_compile import C, S, T, U


def source_sides(formula, scale):
    from .exam_trigonometric_methods import parse_equation
    from .exam_trigonometric_poles import compile_atoms

    values, atoms, _ = parse_equation(formula)
    atoms = {s: replace(a, coefficient=a.coefficient / scale) for s, a in atoms.items()}
    compiled, _ = compile_atoms(atoms)
    return tuple(sp.cancel(v.xreplace(compiled)) for v in values)


def prepare_division(equation, formula, parent_html):
    text = " ".join(
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
        .split()
    )
    if set(equation.poles) != {S, C} or not re.search(r"раздел(?:ить|им)\s+на", text):
        return equation
    left, right = source_sides(formula, equation.scale)
    for ratio in (T, U):
        value = S / C if ratio == T else C / S
        divided = tuple(sp.cancel(v / value) for v in (left, right))
        residual = sp.expand(divided[0] - divided[1])
        if residual.free_symbols not in ({S}, {C}):
            continue
        variable = next(iter(residual.free_symbols))
        if (
            not residual.is_polynomial(variable)
            or sp.degree(residual, variable) != 1
            or any(
                not v.is_polynomial(variable) or sp.degree(v, variable) > 1
                for v in divided
            )
        ):
            continue
        return replace(
            equation,
            raw=residual,
            factored_source=None,
            cleared_denominator=None,
            ratio_division=(ratio, *divided),
        )
    return equation


def division_proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    ratio, left, right = a.ratio_division
    angle = argument(a.scale)
    html = line(a.original)
    html += "<p>Запишем исходную область определения до сокращения:</p>"
    for pole in a.poles:
        html += line(formula(pole, angle) + r"\ne0")
    inverse = U if ratio == T else T
    html += line(r"\frac{1}{" + formula(inverse, angle) + "}=" + formula(ratio, angle))
    html += "<p>На этой области определения тригонометрическое отношение определено и ненулевое. Поэтому обе части можно разделить на него:</p>"
    html += line(formula(ratio, angle) + r"\ne0")
    html += line(formula(left, angle) + "=" + formula(right, angle))
    html += line(formula(a.raw, angle) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch, allowed_residues=branch.residues, angle=angle, root_scale=a.scale
        )
    return "<p>Упростим уравнение на исходной области определения:</p>", html


def checked_levels(a, branch):
    from .exam_trigonometric_inverse import angles
    from .exam_trigonometric_proof import formula, series_lines
    from .exam_trigonometric_variants import argument

    angle = argument(a.scale)
    html = ""
    for value in branch.excluded:
        if branch.variable not in (S, C):
            continue
        other = C if branch.variable == S else S
        delta = sp.simplify(1 - value**2)
        html += line(
            formula(branch.variable, angle)
            + "="
            + sp.latex(value)
            + r"\quad\Longrightarrow\quad"
            + formula(other**2, angle)
            + "=1-("
            + sp.latex(value)
            + ")^2="
            + sp.latex(delta)
        )
        for pole in a.poles:
            reduced = sp.expand(pole.subs(branch.variable, value))
            reduced = sp.rem(reduced, other**2 - delta, other)
            if reduced == 0:
                html += line(formula(pole, angle) + "=0")
                html += "<p>Исходный знаменатель равен нулю; значение исключаем до вычисления углов.</p>"
                break
    for value in branch.values:
        for q in angles(branch.variable, value, a.allow_inverse):
            if q in branch.residues:
                continue
            sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
            bad = next((p for p in a.poles if sp.simplify(p.subs(sub)) == 0), None)
            if bad is not None:
                html += line(
                    series_lines(
                        ((q / a.scale, 2 / a.scale),), sine_inverse=a.sine_inverse
                    )[0]
                )
                html += line(formula(bad, angle) + "=0")
                html += "<p>Эта серия обращает исходный знаменатель в нуль, поэтому её исключаем.</p>"
    return html


def ratio_fraction_proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    angle = argument(a.scale)
    html = (
        line(a.original)
        + "<p>Дробь равна нулю, когда её числитель равен нулю, а все исходные знаменатели отличны от нуля:</p>"
    )
    for pole in a.poles:
        html += line(formula(pole, angle) + r"\ne0")
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value, angle))
    html += "<p>Разложим исходный числитель на множители, сохраняя ограничения знаменателя:</p>"
    html += line(formula(a.raw, angle) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch,
            factorization=True,
            allowed_residues=branch.residues,
            angle=angle,
            root_scale=a.scale,
        )
        for value in branch.excluded:
            replacement = {S: value * C} if branch.variable == T else {C: value * S}
            for pole in a.poles:
                if sp.simplify(pole.subs(replacement)) == 0:
                    html += line(
                        formula(branch.variable, angle)
                        + "="
                        + sp.latex(value)
                        + r"\quad\Longrightarrow\quad"
                        + formula(pole, angle)
                        + "=0"
                    )
                    html += "<p>Эта ветвь обращает исходный знаменатель в нуль и исключается.</p>"
                    break
    return "<p>Решим уравнение как равенство дроби нулю:</p>", html


def doubled_pole_conditions(a):
    from .exam_trigonometric_proof import pi
    from .exam_trigonometric_variants import argument

    html = ""
    for pole in a.poles:
        coefficient = pole.coeff(S * C)
        constant = pole.subs({S: 0, C: 0})
        if coefficient == 0 or sp.expand(pole - coefficient * S * C - constant) != 0:
            continue
        level = sp.simplify(-2 * constant / coefficient)
        if level not in (sp.S.One, -sp.S.One):
            continue
        html += line(r"\sin(" + argument(2 * a.scale) + r")\ne " + sp.latex(level))
        html += line(
            r"x\ne "
            + pi(level / (4 * a.scale))
            + "+"
            + pi(1 / a.scale)
            + r" n,\quad n\in\mathbb Z"
        )
    return html
