"""Certify complete log identities without cancelling their original domains."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_logarithmic_input import Atom
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_identity_style import figure_stage, parent_kind
from .logarithm_arithmetic import power

Z = sp.Symbol("z", real=True)


@dataclass(frozen=True)
class LogIdentity:
    kind: str
    atoms: tuple
    texts: tuple
    level: sp.Expr
    log_value: sp.Expr
    converted: sp.Expr
    polynomial: sp.Expr | None
    substitution: str
    stage: str


def equal(first, second):
    return sp.rem(sp.expand(first - second), S * S + C * C - 1, S) == 0


def repeated_log_value(polynomial):
    values = roots(polynomial.subs(Z, X))
    if len(values) != 1 or values[0] not in (-1, 1):
        raise UnsupportedCondition(
            "the reviewed logarithm quadratic needs one repeated unit level"
        )
    return values[0]


def power_identity(value, atoms, poles):
    if len(atoms) != 1:
        raise UnsupportedCondition(
            "one original variable log is required for the base-power identity"
        )
    a = atoms[0]
    if (
        a.base.free_symbols not in ({S}, {C})
        or sp.Poly(a.base, S, C).total_degree() != 1
    ):
        raise UnsupportedCondition(
            "the base-power identity needs an original sine/cosine base"
        )
    exponent = next(
        (sp.Integer(n) for n in range(1, 5) if equal(a.argument, a.base**n)), None
    )
    if (
        exponent is None
        or value.coeff(a.symbol) not in (-1, 1)
        or sp.degree(value, a.symbol) != 1
    ):
        raise UnsupportedCondition(
            "the complete equation must retain one first-power log of its own base power"
        )
    converted = sp.cancel(value.subs(a.symbol, exponent))
    numerator, denominator = sp.fraction(converted)
    if converted.free_symbols not in ({S}, {C}):
        raise UnsupportedCondition(
            "one reciprocal trigonometric polynomial is required after the log identity"
        )
    variable = next(iter(converted.free_symbols))
    if (
        denominator.subs(variable, 0) != 0
        or sp.Poly(denominator, variable).length() != 1
        or not any(equal(p, variable) or equal(p, -variable) for p in poles)
    ):
        raise UnsupportedCondition(
            "every cleared reciprocal denominator must already be an original pole"
        )
    reciprocal = sp.cancel(converted.subs(variable, 1 / Z))
    if (
        not reciprocal.is_polynomial(Z)
        or sp.degree(reciprocal, Z) != 2
        or sp.degree(numerator, variable) > 2
    ):
        raise UnsupportedCondition(
            "the parent's reciprocal-function quadratic is required"
        )
    return numerator, exponent, converted, reciprocal


def chain_identity(value, atoms, level):
    if len(atoms) != 2:
        raise UnsupportedCondition(
            "two original logs are required for a chain identity"
        )
    a, b = atoms
    if (
        a.base.free_symbols
        or a.base.is_positive is not True
        or a.base == 1
        or not b.base.free_symbols
        or not equal(a.argument, b.base)
        or sp.expand(value - (a.symbol * b.symbol - level)) != 0
    ):
        raise UnsupportedCondition(
            "the complete original product must be log_a b times log_b c"
        )
    target = power(a.base, level)
    raw = sp.expand(b.argument - target)
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 2:
        raise UnsupportedCondition(
            "the chain identity needs a quadratic trigonometric argument"
        )
    return raw, level, raw, None


def substitution_identity(value, atoms, level, kind):
    if len(atoms) != 2:
        raise UnsupportedCondition(
            "two original logs are required for the reciprocal substitution"
        )
    a, b = atoms
    if kind == "reciprocal":
        if (
            not equal(a.base, b.argument)
            or not equal(a.argument, b.base)
            or sp.expand(value - (a.symbol + b.symbol - level)) != 0
        ):
            raise UnsupportedCondition(
                "the complete sum must contain two reciprocal original logarithms"
            )
        polynomial = Z * Z - level * Z + 1
        log_value = repeated_log_value(polynomial)
        raw = (
            sp.expand(a.argument - a.base)
            if log_value == 1
            else sp.expand(a.argument * a.base - 1)
        )
    else:
        if (
            {a.argument, b.argument} != {S, C}
            or not equal(a.base, b.base)
            or not equal(a.base, a.argument * b.argument)
            or sp.expand(value - (a.symbol * b.symbol - level)) != 0
        ):
            raise UnsupportedCondition(
                "the two original positive arguments must have their product as common base"
            )
        polynomial = sp.expand(level * (1 + Z) ** 2 - Z)
        log_value = repeated_log_value(polynomial)
        if log_value != 1:
            raise UnsupportedCondition(
                "positive-quadrant reciprocal logs require the repeated level one"
            )
        raw = sp.expand(b.argument - a.argument)
    return raw, log_value, raw, polynomial


def certify_identity(value, logs, values, poles, parent_html, angles):
    from .exam_trigonometric_log_equality import original_text

    method = parent_kind(parent_html)
    if method is None:
        return None
    kind, name = method
    atoms = tuple(
        Atom(base, arg, False, entry[0])
        for entry, (base, arg) in zip(
            logs, zip(values[::2], values[1::2], strict=True), strict=True
        )
    )
    if not atoms or any(
        a.base.free_symbols - {S, C}
        or a.argument.free_symbols - {S, C}
        or not a.base.is_polynomial(S, C)
        or not a.argument.is_polynomial(S, C)
        or sp.Poly(a.base, S, C).total_degree() > 2
        or sp.Poly(a.argument, S, C).total_degree() > 2
        for a in atoms
    ):
        raise UnsupportedCondition(
            "bounded original trigonometric polynomial bases and arguments are required"
        )
    if any(
        a.coefficient not in (1, 2)
        or a.shift not in (0, -sp.Rational(1, 2), sp.Rational(1, 2))
        or (kind != "power" and a.shift)
        for a in angles.values()
    ) or (poles and kind != "power"):
        raise UnsupportedCondition(
            "the original angles or poles are outside the reviewed logarithm identity"
        )
    symbols = tuple(a.symbol for a in atoms)
    level = -value.subs(dict.fromkeys(symbols, 0)) if kind != "power" else sp.S.Zero
    if kind != "power" and (
        level.is_Rational is not True or abs(level) > 20 or level.q > 12
    ):
        raise UnsupportedCondition(
            "one bounded rational log identity level is required"
        )
    if kind == "power":
        raw, log_value, converted, polynomial = power_identity(value, atoms, poles)
    elif kind == "chain":
        if (
            len(atoms) == 2
            and atoms[0].base.free_symbols
            and not atoms[1].base.free_symbols
        ):
            atoms = tuple(reversed(atoms))
        raw, log_value, converted, polynomial = chain_identity(value, atoms, level)
    else:
        raw, log_value, converted, polynomial = substitution_identity(
            value, atoms, level, kind
        )
    text_by_symbol = {e[0]: (original_text(e[3]), original_text(e[4])) for e in logs}
    texts = tuple(text_by_symbol[a.symbol] for a in atoms)
    data = LogIdentity(
        kind,
        atoms,
        texts,
        level,
        log_value,
        converted,
        polynomial,
        name,
        figure_stage(parent_html, kind),
    )
    return raw, data


def build_equation(raw, data, identities, poles):
    from .exam_trigonometric_log_equality import LogEquality
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_methods import Equation

    return Equation(
        raw,
        identities,
        sp.S.One,
        poles=poles,
        log_product=LogProduct(
            raw,
            None,
            None,
            None,
            selection_image_position="after-steps"
            if data.kind == "chain"
            else "selection",
            equality=LogEquality(
                "identity", data.log_value, None, "", "", identity=data
            ),
        ),
    )
