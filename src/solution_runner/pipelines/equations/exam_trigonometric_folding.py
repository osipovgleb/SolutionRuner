"""Fold typed products and square differences before expanding high angle multiples."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .trig_symbolic_parser import SymbolicAtom

X = sp.Symbol("x", real=True)


def fold(values, atoms, denominators, preferred_scale):
    if any(d.free_symbols for d in denominators):
        return values, atoms, None, None
    expression = values[0] - values[1]
    symbols = tuple(atoms)
    poly = sp.Poly(expression, *symbols)
    base = sp.gcd_list([abs(a.coefficient) for a in atoms.values()])
    coefficients = [abs(atoms[s].coefficient) for s in symbols]
    if (
        preferred_scale == 2 * base
        and poly.total_degree() > 2
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
    difference = sp.trigsimp(actual - rewritten)
    if difference != 0:
        difference = sp.trigsimp(sp.expand(sp.expand_trig(difference)))
    if difference != 0:
        raise UnsupportedCondition("the product identity must be verified exactly")
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
