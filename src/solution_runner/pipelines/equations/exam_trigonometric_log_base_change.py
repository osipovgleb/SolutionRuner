"""Keep original reciprocal-log poles while reducing a squared base substitution."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S


@dataclass(frozen=True)
class SquareBaseChange:
    variable: sp.Symbol
    offset: sp.Rational
    weight: sp.Rational
    target: sp.Expr


def reciprocal(value, atoms, poles):
    if len(atoms) != 2:
        raise UnsupportedCondition(
            "two original logarithms are required for reciprocal base change"
        )
    variable = next((a for a in atoms if a.base.free_symbols), None)
    fixed = next((a for a in atoms if not a.base.free_symbols), None)
    if (
        variable is None
        or fixed is None
        or fixed.base.is_Rational is not True
        or not 1 < fixed.base <= 100
        or fixed.argument != variable.base
        or poles != (fixed.symbol,)
    ):
        raise UnsupportedCondition(
            "the original fixed-log denominator must share the variable base exactly"
        )
    remainder = sp.cancel(value - variable.symbol + 1 / fixed.symbol)
    level = -remainder
    if level.is_Integer is not True or not 0 <= level <= 4:
        raise UnsupportedCondition(
            "the complete equation must be log_B A = k + 1/log_d B"
        )
    return variable, fixed, level, (sp.expand(variable.base - 1),)


def certify(value, atoms, poles, angles):
    variable, fixed, level, mapped_poles = reciprocal(value, atoms, poles)
    base, argument = variable.base, variable.argument
    if (
        level != 2
        or base.free_symbols not in ({S}, {C})
        or not base.is_polynomial(S, C)
    ):
        raise UnsupportedCondition(
            "a quadratic squared-function base with level two is required"
        )
    z = next(iter(base.free_symbols))
    offset, weight = base.subs(z, 0), -base.coeff(z, 2)
    if (
        offset.is_Rational is not True
        or weight.is_Rational is not True
        or not 1 < offset <= 100
        or not 0 < weight <= 100
        or sp.expand(base - offset + weight * z * z) != 0
        or sp.expand(argument - offset**2 + weight**2 * z**4) != 0
        or any(
            a.coefficient != 1 or a.shift or a.function not in ("sin", "cos")
            for a in angles.values()
        )
    ):
        raise UnsupportedCondition(
            "the original argument must factor as (a-t)(a+t) with t=b sin²x or b cos²x"
        )
    target = sp.cancel(offset * (fixed.base - 1) / (fixed.base + 1))
    data = SquareBaseChange(z, offset, weight, target)
    return sp.expand(weight * z * z - target), (variable, fixed), mapped_poles, data


def identity(value, atoms, logs, poles, parent_html, angles):
    from .exam_trigonometric_log_base_change_style import figure_stage, review
    from .exam_trigonometric_log_equality import original_text
    from .exam_trigonometric_log_identity import LogIdentity, Z

    raw, atoms, _, details = certify(value, atoms, poles, angles)
    name = review(parent_html)
    source = {e[0]: (original_text(e[3]), original_text(e[4])) for e in logs}
    polynomial = sp.expand(
        (atoms[1].base + 1) * Z - details.offset * (atoms[1].base - 1)
    )
    data = LogIdentity(
        "base_square",
        atoms,
        tuple(source[a.symbol] for a in atoms),
        sp.Integer(2),
        sp.S.One,
        details.weight * details.variable**2,
        polynomial,
        name,
        figure_stage(parent_html),
        details,
    )
    return raw, data
