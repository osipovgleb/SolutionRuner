"""Fold typed products and square differences before expanding high angle multiples."""

from math import gcd, lcm

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import S
from .exam_trigonometric_power_identity import paired_sixths
from .trig_symbolic_parser import SymbolicAtom

X = sp.Symbol("x", real=True)


def common_scale(atoms):
    values = [abs(sp.sympify(a.coefficient)) for a in atoms.values()]
    if not values or any(v.is_Rational is not True or v == 0 for v in values):
        raise UnsupportedCondition("a common positive rational base angle is required")
    return sp.Rational(gcd(*(v.p for v in values)), lcm(*(v.q for v in values)))


def fold(values, atoms, denominators, preferred_scale, *, sine_square=False):
    if any(d.free_symbols for d in denominators):
        return values, atoms, None, None
    expression = values[0] - values[1]
    symbols = tuple(atoms)
    poly = sp.Poly(expression, *symbols)
    base = common_scale(atoms)
    coefficients = [abs(atoms[s].coefficient) for s in symbols]
    if (
        preferred_scale == 2 * base
        and poly.total_degree() > 2
        and not (sine_square and paired_sixths(expression, atoms))
        and all(
            power % 2 == 0
            for powers in poly.monoms()
            for coefficient, power in zip(coefficients, powers)
            if coefficient == base
        )
    ):
        return values, atoms, None, None
    mixed = any(
        len({c for c, power in zip(coefficients, powers) if power}) > 1
        for powers in poly.monoms()
    )
    square_difference = (
        preferred_scale == 2 * base
        and poly.total_degree() <= 2
        and any(
            power == 2 and c == base
            for powers in poly.monoms()
            for c, power in zip(coefficients, powers)
        )
    )
    if not (mixed or square_difference or poly.total_degree() == 6):
        return values, atoms, None, None
    actual = expression.xreplace(
        {
            s: (sp.sin if a.function == "sin" else sp.cos)(
                a.coefficient * X + a.shift * sp.pi
            )
            for s, a in atoms.items()
        }
    )
    from .exam_trigonometric_power_identity import fold_sixth

    folded_actual, power_angle = fold_sixth(actual)
    rewritten = sp.expand(
        folded_actual
        if power_angle is not None
        else sp.trigsimp(folded_actual, method="fu")
    )
    verify_identity(actual, rewritten)
    functions = sorted(rewritten.atoms(sp.sin, sp.cos), key=sp.default_sort_key)
    if not functions:
        raise UnsupportedCondition("the folded equation must retain a variable angle")
    substitutions, folded = {}, {}
    for i, function in enumerate(functions):
        argument = sp.expand(function.args[0])
        coefficient = argument.coeff(X)
        shift = sp.cancel((argument - coefficient * X) / sp.pi)
        if (
            coefficient.is_Rational is not True
            or coefficient == 0
            or abs(coefficient) > 100
            or coefficient.q > 4
            or shift.is_Rational is not True
            or (12 * shift).is_Integer is not True
        ):
            raise UnsupportedCondition(
                "the folded angles must stay in the reviewed affine grammar"
            )
        symbol = sp.Symbol("F" + str(i), real=True)
        name = "sin" if function.func == sp.sin else "cos"
        substitutions[function] = symbol
        folded[symbol] = SymbolicAtom(
            name,
            coefficient,
            shift,
            r"\alpha",
            "\\" + name + "(" + sp.latex(argument) + ")",
        )
    return (
        [rewritten.xreplace(substitutions), sp.Integer(0)],
        folded,
        rewritten,
        power_angle,
    )


def verify_identity(actual, rewritten):
    difference = sp.trigsimp(actual - rewritten)
    if difference != 0:
        difference = sp.trigsimp(sp.expand(sp.expand_trig(difference)))
    if difference != 0:
        raise UnsupportedCondition("the product identity must be verified exactly")


def normalize_base(
    values, atoms, denominators, preferred, preferred_scale, preserve_products
):
    from dataclasses import replace

    from .exam_trigonometric_pi_scale import normalize

    atoms, unit = normalize(atoms, denominators)
    preferred_scale /= unit
    rewritten, power_angle = None, None
    if not preserve_products:
        values, atoms, rewritten, power_angle = fold(
            values, atoms, denominators, preferred_scale, sine_square=(preferred == S)
        )
    scale = common_scale(atoms)
    for symbol, atom in tuple(atoms.items()):
        multiple = sp.cancel(atom.coefficient / scale)
        if multiple.is_Integer is not True:
            raise UnsupportedCondition(
                "each angle must be an exact integer multiple of its base"
            )
        atoms[symbol] = replace(atom, coefficient=int(multiple))
    return values, atoms, scale, unit, preferred_scale, rewritten, power_angle
