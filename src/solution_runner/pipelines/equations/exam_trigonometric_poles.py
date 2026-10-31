"""Cancel ratio products only on the full original nonzero domain."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S


def compile_quotients(values, atoms, denominators):
    from .exam_trigonometric_methods import Equation, shifted_atom

    compiled = {}
    poles = set()
    for symbol, atom in atoms.items():
        if atom.function in ("tg", "ctg"):
            if abs(atom.coefficient) != 1 or not atom.shift.is_Integer:
                raise UnsupportedCondition(
                    "ratio products require one angle and integer-pi shifts"
                )
            numerator, denominator = (S, C) if atom.function == "tg" else (C, S)
            compiled[symbol] = atom.coefficient * numerator / denominator
            poles.add(denominator)
        elif (
            atom.function in ("sin", "cos")
            and atom.coefficient.is_Integer
            and abs(atom.coefficient) <= 4
        ):
            compiled[symbol] = shifted_atom(atom).xreplace({NUMERIC_S: S, NUMERIC_C: C})
        else:
            raise UnsupportedCondition("unreviewed ratio-product angle")
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
    if (
        denominator.free_symbols
        or not raw.is_polynomial(S, C)
        or raw == 0
        or sp.Poly(raw, S, C).total_degree() > 4
    ):
        raise UnsupportedCondition(
            "the reviewed ratio products must cancel to a nonzero polynomial"
        )
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), compiled[s]) for s, a in atoms.items()
        )
    )
    return Equation(
        sp.expand(raw), identities, sp.Integer(1), tuple(sorted(poles, key=str))
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    html = "<p>Запишем область определения исходных тангенса и котангенса до сокращения:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += "<p>В этой области используем определения тригонометрических отношений:</p>"
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    html += line(formula(a.raw) + "=0")
    if a.raw != a.reduced:
        html += line(formula(a.reduced) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch, allowed_residues=branch.residues, factorization=a.factorization
        )
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
    return (
        "<p>Упростим произведение тригонометрических отношений с сохранением ОДЗ:</p>",
        html,
    )
