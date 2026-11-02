"""Recognize reviewed shifted functions in an affine sine/cosine factor."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def branch(expression, *, allow_inverse=False):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_inverse import angles, ordered

    if expression.free_symbols != {S, C} or not expression.is_polynomial(S, C):
        return None
    if sp.Poly(expression, S, C).total_degree() != 1:
        return None
    a, b = expression.coeff(S), expression.coeff(C)
    constant = expression.subs({S: 0, C: 0})
    if not a or not b or not constant:
        return None
    amplitude = sp.sqrt(sp.simplify(a * a + b * b))
    phases = [
        sp.Rational(n, 12)
        for n in range(-11, 13)
        if sp.simplify(amplitude * sp.cos(sp.pi * n / 12) - a) == 0
        and sp.simplify(amplitude * sp.sin(sp.pi * n / 12) - b) == 0
    ]
    if len(phases) != 1:
        return None
    phase = phases[0]
    value = sp.simplify(-constant / amplitude)
    from ..word_problems.common import UnsupportedCondition

    try:
        roots = angles(S, value, allow_inverse)
    except UnsupportedCondition:
        return None
    residues = ordered((q - phase) % 2 for q in roots)
    return Branch(
        S,
        S - value,
        (value,),
        (value,),
        residues,
        original=expression,
        angle_shift=phase,
    )


def notation(branches, parent_html, *, scale=sp.S.One, allow_inverse=False):
    from bs4 import BeautifulSoup

    from .exam_trigonometric_shifted import candidates, formula

    functions = {
        name
        for node in BeautifulSoup(parent_html, "html.parser").select(
            "[data-inline-latex]"
        )
        for name, _, _ in candidates(
            formula(node["data-inline-latex"]), argument_scale=scale
        )
    }
    if functions != {"cos"}:
        return branches
    source_forms = {
        (name, shift)
        for node in BeautifulSoup(parent_html, "html.parser").select(
            "[data-inline-latex]"
        )
        for name, _, shift in candidates(
            formula(node["data-inline-latex"]), argument_scale=scale
        )
    }
    result = []
    for b in branches:
        if b.angle_shift:
            phase = (b.angle_shift - sp.Rational(1, 2) + 1) % 2 - 1
            b = replace(
                b, variable=C, polynomial=C - b.candidates[0], angle_shift=phase
            )
        b = orient(b, source_forms, parent_html, scale, allow_inverse=allow_inverse)
        result.append(b)
    return tuple(result)


def orient(b, forms, html, scale, *, allow_inverse=False):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    if len(forms) != 1 or b.original is None:
        return b
    name, shift = next(iter(forms))
    variable = S if name == "sin" else C
    basis = (
        S * sp.cos(shift * sp.pi) + C * sp.sin(shift * sp.pi)
        if variable == S
        else C * sp.cos(shift * sp.pi) - S * sp.sin(shift * sp.pi)
    )
    coefficient = next(v for v in (S, C) if basis.coeff(v) != 0)
    weight = sp.simplify(b.original.coeff(coefficient) / basis.coeff(coefficient))
    constant = b.original.subs({S: 0, C: 0})
    if (
        weight.is_negative is not True
        or sp.simplify(b.original - weight * basis - constant) != 0
    ):
        return b
    value = sp.simplify(-constant / weight)
    actual = tuple(
        ((q - shift) / scale, p / scale)
        for q, p in level_series(variable, value, allow_inverse)
    )
    source = tuple((q, p) for q, p, _ in affine_families(html))
    source = (
        source
        if len(source) == len(actual) and equivalent_series(source, actual)
        else actual
    )
    return replace(
        b,
        variable=variable,
        original=-b.original,
        polynomial=variable - value,
        candidates=(value,),
        values=(value,),
        angle_shift=shift,
        phase_series=source,
    )


def paired_family(branch, root_scale=sp.S.One):
    from .exam_trigonometric_inverse import angles, ordered
    from .exam_trigonometric_proof import K

    if branch.variable != C or len(branch.candidates) != 1 or not branch.angle_shift:
        return None
    roots = angles(C, branch.candidates[0], True)
    if (
        all(q.is_Rational for q in roots)
        or ordered((q - branch.angle_shift) % 2 for q in roots) != branch.residues
    ):
        return None
    offset = -branch.angle_shift * sp.pi / root_scale
    return (
        "x="
        + (sp.latex(offset) if offset else "")
        + r"\pm "
        + sp.latex(sp.acos(branch.candidates[0]) / root_scale, inv_trig_style="full")
        + "+"
        + sp.latex(2 * sp.pi * K / root_scale)
    )


def proof(branch, angle, root_scale, allowed_residues=None, *, allow_inverse=False):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import formula, series_lines

    expression = branch.original
    amplitude = sp.sqrt(
        sp.simplify(expression.coeff(S) ** 2 + expression.coeff(C) ** 2)
    )
    constant = expression.subs({S: 0, C: 0})
    shifted = (
        r"\left(" + angle + "+(" + sp.latex(branch.angle_shift * sp.pi) + r")\right)"
    )
    html = line(formula(expression, angle) + "=0")
    name = "синуса" if branch.variable == S else "косинуса"
    html += (
        "<p>Применим формулу "
        + name
        + " суммы и получим уравнение для сдвинутого угла:</p>"
    )
    html += line(
        formula(expression, angle)
        + "="
        + formula(amplitude * branch.variable + constant, shifted)
    )
    html += line(
        formula(branch.variable, shifted) + "=" + sp.latex(branch.candidates[0])
    )
    paired = paired_family(branch, root_scale) if allow_inverse else None
    if paired is not None and allowed_residues is None:
        return html + line(paired + r",\quad k\in\mathbb Z")
    series = tuple(
        ((q - branch.angle_shift) / root_scale, period / root_scale)
        for q, period in level_series(
            branch.variable, branch.candidates[0], allow_inverse
        )
    )
    series = branch.phase_series or series
    for text in series_lines(series):
        html += line(text + r",\quad k\in\mathbb Z")
    if allowed_residues is not None:
        html += "<p>После проверки исходной области определения оставляем серии:</p>"
        for text in series_lines(
            tuple((q, p) for q, p in series if (q * root_scale) % 2 in allowed_residues)
            if branch.phase_series
            else tuple((q / root_scale, 2 / root_scale) for q in allowed_residues)
        ):
            html += line(text + r",\quad k\in\mathbb Z")
    return html
