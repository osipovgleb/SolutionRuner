"""Solve a reviewed function fraction on every original ratio and explicit domain."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U


def compile_fraction(values, atoms, denominators, preferred):
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_poles import compile_atoms
    from .exam_trigonometric_rational import reviewed_numerator

    numerator, denominator = sp.fraction(values[0] - values[1])
    if not denominator.free_symbols:
        return None
    original = [d for d in denominators if d.free_symbols]
    compiled, intrinsic = compile_atoms(atoms)
    converted = [sp.fraction(sp.cancel(d.xreplace(compiled)))[0] for d in original]
    if all(sp.Poly(d, S, C).length() == 1 for d in converted):
        return None
    if len(original) != 1 or any(
        not d.is_polynomial(S, C) or sp.Poly(d, S, C).total_degree() > 2
        for d in converted
    ):
        raise UnsupportedCondition(
            "one bounded explicit function denominator is required"
        )
    poles = tuple(sorted(intrinsic | set(converted), key=str))
    fraction = sp.together((values[0] - values[1]).xreplace(compiled))
    functions = {atoms[s].function for s in numerator.free_symbols}
    if len(functions) == 1 and functions <= {"tg", "ctg"}:
        variable = T if functions == {"tg"} else U
        if any(
            a.coefficient != 1 or not a.shift.is_Integer
            for a in atoms.values()
            if a.function in functions
        ):
            raise UnsupportedCondition(
                "the fraction numerator requires an unshifted ratio"
            )
        raw = sp.expand(
            numerator.xreplace(dict.fromkeys(numerator.free_symbols, variable))
        )
        if sp.degree(raw, variable) not in (1, 2):
            raise UnsupportedCondition(
                "the ratio numerator must be linear or quadratic"
            )
    else:
        raw = reviewed_numerator(sp.expand(numerator.xreplace(compiled)), preferred)
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), compiled[s]) for s, a in atoms.items()
        )
    )
    return Equation(raw, identities, sp.S.One, poles, fraction=fraction)
