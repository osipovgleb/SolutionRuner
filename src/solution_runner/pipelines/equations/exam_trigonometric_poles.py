"""Cancel ratio products only on the full original nonzero domain."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S


def compile_quotients(values, atoms, denominators, *, preferred=None):
    from .exam_trigonometric_methods import Equation

    compiled, poles = compile_atoms(atoms)
    for d in denominators:
        numerator, _ = sp.fraction(sp.cancel(d.xreplace(compiled)))
        if numerator.free_symbols:
            p = sp.Poly(numerator, S, C)
            if p.length() != 1:
                raise UnsupportedCondition(
                    "additional poles must be powers of sine and cosine"
                )
            poles.update(numerator.free_symbols)
    expression = sp.cancel((values[0] - values[1]).xreplace(compiled))
    raw, denominator = sp.fraction(expression)
    if not raw.is_polynomial(S, C) or raw == 0 or sp.Poly(raw, S, C).total_degree() > 4:
        raise UnsupportedCondition(
            "the reviewed ratio products must cancel to a nonzero polynomial"
        )
    cleared = None
    source = None
    if denominator.free_symbols:
        if (
            not denominator.is_polynomial(S, C)
            or sp.Poly(denominator, S, C).length() != 1
            or sp.Poly(denominator, S, C).total_degree() not in (1, 2)
            or not denominator.free_symbols <= poles
        ):
            raise UnsupportedCondition(
                "cleared denominators must be bounded powers covered by the original domain"
            )
        cleared, source = denominator, raw
        if sp.Poly(denominator, S, C).total_degree() == 1:
            raw = sp.expand(sp.rem(raw, S * S + C * C - 1, S if S in poles else C))
        elif preferred in (S, C):
            reduced = sp.expand(
                sp.rem(raw, S * S + C * C - 1, S if preferred == C else C)
            )
            if (
                reduced.free_symbols == {preferred}
                and sp.degree(reduced, preferred) <= 2
            ):
                raw = reduced
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), compiled[s]) for s, a in atoms.items()
        )
    )
    return Equation(
        sp.expand(raw),
        identities,
        sp.Integer(1),
        tuple(sorted(poles, key=str)),
        factored_source=source,
        cleared_denominator=cleared,
    )


def compile_atoms(atoms):
    from .exam_trigonometric_methods import shifted_atom

    compiled = {}
    poles = set()
    for symbol, atom in atoms.items():
        if atom.function in ("tg", "ctg"):
            if abs(atom.coefficient) != 1 or (2 * atom.shift).is_Integer is not True:
                raise UnsupportedCondition(
                    "ratio products require unit angles and half-pi shifts"
                )
            sine = shifted_atom(replace(atom, function="sin")).xreplace(
                {NUMERIC_S: S, NUMERIC_C: C}
            )
            cosine = shifted_atom(replace(atom, function="cos")).xreplace(
                {NUMERIC_S: S, NUMERIC_C: C}
            )
            numerator, denominator = (
                (sine, cosine) if atom.function == "tg" else (cosine, sine)
            )
            if denominator.free_symbols not in ({S}, {C}):
                raise UnsupportedCondition(
                    "the ratio denominator must be sine or cosine"
                )
            compiled[symbol] = sp.cancel(numerator / denominator)
            poles.update(denominator.free_symbols)
        elif (
            atom.function in ("sin", "cos")
            and atom.coefficient.is_Integer
            and abs(atom.coefficient) <= 4
        ):
            compiled[symbol] = shifted_atom(atom).xreplace({NUMERIC_S: S, NUMERIC_C: C})
        else:
            raise UnsupportedCondition("unreviewed ratio-product angle")
    return compiled, poles


def proof(a):
    from functools import partial

    from .exam_trigonometric_proof import formula as format_formula
    from .exam_trigonometric_proof import polynomial
    from .exam_trigonometric_variants import argument

    theta = argument(a.scale)
    formula = partial(format_formula, angle=theta)

    html = "<p>Запишем область определения исходных тангенса и котангенса до сокращения:</p>"
    if a.cleared_denominator is not None:
        html = "<p>Запишем область определения исходного уравнения:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += "<p>В этой области используем определения тригонометрических отношений:</p>"
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    if a.cleared_denominator is not None:
        html += "<p>Умножим уравнение на знаменатель, ненулевой в исходной области определения:</p>"
        html += line(formula(a.cleared_denominator) + r"\ne0")
        html += line(formula(a.factored_source) + "=0")
        html += line(formula(S * S + C * C) + "=1")
    html += line(formula(a.raw) + "=0")
    if a.raw != a.reduced:
        html += line(formula(a.reduced) + "=0")
    if a.cleared_denominator is not None:
        html += line(formula(sp.factor(a.reduced, extension=True)) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch,
            allowed_residues=branch.residues,
            factorization=a.factorization,
            angle=theta,
            root_scale=a.scale,
        )
        if branch.angle_shift:
            from .exam_trigonometric_phase_domain import proof as excluded_phases

            html += excluded_phases(branch, a.poles, scale=a.scale)
        for value in branch.excluded:
            if abs(value) == 1:
                other = C if branch.variable == S else S
                html += line(
                    formula(branch.variable)
                    + "="
                    + sp.latex(value)
                    + r"\quad\Longrightarrow\quad"
                    + formula(other**2)
                    + "=1-("
                    + sp.latex(value)
                    + r")^2=0"
                )
                html += "<p>Нулевая величина в знаменателе нарушает исходную область определения; эта ветвь исключается.</p>"
    intro = (
        "<p>Решим уравнение, сохраняя исходную область определения:</p>"
        if a.cleared_denominator is not None
        else "<p>Упростим произведение тригонометрических отношений с сохранением ОДЗ:</p>"
    )
    return intro, html
