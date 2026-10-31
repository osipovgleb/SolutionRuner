"""Quadratic substitution in an inverse ratio keeps both original sine/cosine poles."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U


def compile_reciprocal(values, atoms, denominators):
    from .exam_trigonometric_methods import Equation

    functions = {a.function for a in atoms.values()}
    if (
        not any(d.free_symbols for d in denominators)
        or len(functions) != 1
        or not functions <= {"tg", "ctg"}
    ):
        return None
    if any(a.coefficient != 1 or not a.shift.is_Integer for a in atoms.values()):
        raise UnsupportedCondition(
            "inverse ratio quadratics require one unshifted base function"
        )
    variable = T if functions == {"tg"} else U
    compiled = dict.fromkeys(atoms, variable)
    for denominator in denominators:
        pole = sp.expand(denominator.xreplace(compiled))
        if pole.free_symbols and (
            pole.free_symbols != {variable}
            or not pole.is_polynomial(variable)
            or sp.Poly(pole, variable).length() != 1
            or sp.degree(pole, variable) > 2
        ):
            raise UnsupportedCondition(
                "inverse ratio denominators must be nonzero powers up to two"
            )
    expression = sp.cancel((values[0] - values[1]).xreplace(compiled))
    parameter = sp.Symbol("t", real=True)
    reciprocal = sp.cancel(expression.subs(variable, 1 / parameter))
    raw, _ = sp.fraction(expression)
    if (
        not reciprocal.is_polynomial(parameter)
        or sp.degree(reciprocal, parameter) != 2
        or not raw.is_polynomial(variable)
        or sp.degree(raw, variable) not in (1, 2)
    ):
        raise UnsupportedCondition(
            "the inverse ratio substitution must produce a genuine quadratic"
        )
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), variable) for a in atoms.values()
        )
    )
    return Equation(sp.expand(raw), identities, sp.S.One, (S, C), reciprocal=reciprocal)


def validate_axis(entry, a):
    axis = entry.get("ratio_axis")
    if axis is None:
        return
    variable = {"tg": T, "ctg": U}.get(axis.get("function"))
    if (
        variable is None
        or a.reciprocal is None
        or a.scale != 1
        or a.translation
        or len(a.branches) != 1
        or a.branches[0].variable != variable
        or set(a.branches[0].values) != set(map(sp.Rational, axis["levels"]))
    ):
        raise UnsupportedCondition(
            "the prepared ratio axis must match the inverse substitution and levels"
        )
