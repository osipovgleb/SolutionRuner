"""Solve the two zero factors, checking every original logarithm and ratio pole."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .power_arithmetic import clean

if TYPE_CHECKING:
    from .exam_trigonometric_log_equality import LogEquality
    from .exam_trigonometric_log_radical import RadicalLog


@dataclass(frozen=True)
class LogProduct:
    factor: sp.Expr
    base: sp.Expr | None
    argument: sp.Expr | None
    denominator: tuple | None
    divide: sp.Expr = sp.S.One
    log_first: bool = False
    nonzero_bound: sp.Expr | None = None
    double_angle: tuple | None = None
    selection_image_position: str = "selection"
    level_ascending: bool | None = None
    domain_labels: bool = False
    radical: "RadicalLog | None" = None
    equality: "LogEquality | None" = None


def compile_product(formula):
    from .exam_trigonometric_log_parser import Parser
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if text.count("=") != 1 or not text.endswith("=0"):
        raise UnsupportedCondition("a complete log-factor product must equal zero")
    atoms, denominators, logs = {}, [], []
    value = (
        Parser(text[:-2].replace("x", r"\alpha"), atoms, denominators, logs)
        .parse()
        .value
    )
    if not logs:
        raise UnsupportedCondition("a variable logarithm factor is required")
    symbols = tuple(item[0] for item in logs)
    values, poles, identities = compile_values(
        [value, *(item[2] for item in logs)], atoms, denominators, extra_symbols=symbols
    )
    value, *arguments = values
    numerator, denominator = sp.fraction(value)
    upstairs = [v for v in symbols if numerator.has(v)]
    downstairs = [v for v in symbols if denominator.has(v)]
    if (
        len(upstairs) > 1
        or len(downstairs) > 1
        or len(upstairs) + len(downstairs) != len(logs)
    ):
        raise UnsupportedCondition(
            "at most one numerator and one denominator log are required"
        )
    log = upstairs[0] if upstairs else sp.S.One
    den_log = downstairs[0] if downstairs else sp.S.One
    factor = sp.cancel(value * den_log / log)
    if factor.free_symbols - {S, C} or any(
        p.has(*symbols) and p != den_log for p in poles
    ):
        raise UnsupportedCondition(
            "uncancelled log powers or extra log denominators are unsupported"
        )
    poles = tuple(p for p in poles if not p.has(*symbols))
    if not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "log products retain only original sine/cosine ratio poles"
        )
    if any(not argument.free_symbols for argument in arguments):
        raise UnsupportedCondition(
            "a log argument must remain nonconstant on compilation"
        )
    for expression in (factor, *arguments):
        num, den = sp.fraction(expression)
        if (
            not num.is_polynomial(S, C)
            or sp.Poly(num, S, C).total_degree() > 4
            or not den.is_polynomial(S, C)
            or sp.Poly(den, S, C).total_degree() > 2
        ):
            raise UnsupportedCondition(
                "bounded rational unit-circle log factors are required"
            )
        circle = S * S + C * C - 1
        reduced_den = sp.rem(den, circle, S)
        if (
            reduced_den == 0
            or not sp.cancel(sp.rem(num, circle, S) / reduced_den).free_symbols
        ):
            raise UnsupportedCondition(
                "a constant unit-circle factor requires a complete-domain method"
            )
    if factor == 0 or not factor.free_symbols:
        raise UnsupportedCondition("a nonconstant nonzero algebraic factor is required")
    index = symbols.index(log) if upstairs else None
    other = symbols.index(den_log) if downstairs else None
    data = LogProduct(
        factor,
        logs[index][1] if index is not None else None,
        arguments[index] if index is not None else None,
        (logs[other][1], arguments[other]) if other is not None else None,
    )
    raw = sp.fraction(factor)[0]
    if data.argument is not None:
        raw *= sp.fraction(data.argument - 1)[0]
    raw = sp.expand(raw)
    return Equation(raw, identities, sp.S.One, poles=poles, log_product=data)


def conditions(compiled):
    data = compiled.log_product
    result = [(p, "nonzero") for p in compiled.poles]
    if compiled.log_polynomial is not None:
        normalization = compiled.log_polynomial.normalization
        arguments = (
            normalization.original_arguments
            if normalization is not None
            else (compiled.log_polynomial.argument,)
        )
        return (*result, *((arg, "positive") for arg in arguments))
    if data.equality is not None and data.equality.variable is not None:
        base = data.equality.variable.base
        return (
            *result,
            (base, "positive"),
            (base - 1, "nonzero"),
            (data.argument, "positive"),
        )
    if data.equality is not None and data.equality.identity is not None:
        from .exam_logarithmic_branches import constraints

        return (*result, *constraints(data.equality.identity.atoms))
    if data.argument is not None:
        result.append((data.argument, "positive"))
    if data.equality is not None and data.equality.other_argument is not None:
        result.append((data.equality.other_argument, "positive"))
    if data.radical is not None:
        result.append((data.factor, "nonnegative"))
        if data.radical.denominator is not None:
            result.append((data.radical.denominator, "positive"))
    if data.denominator:
        argument = data.denominator[1]
        result.extend(((argument, "positive"), (argument - 1, "nonzero")))
    return tuple(result)


def failed(compiled, q):
    from .exam_exponential import X

    substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi), X: q * sp.pi}
    for expression, relation in conditions(compiled):
        value = sp.simplify(expression.subs(substitution))
        if value.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            return expression, relation, value
        if (
            (relation == "positive" and value.is_positive is True)
            or (relation == "nonnegative" and value.is_nonnegative is True)
            or (relation == "nonzero" and value.is_zero is False)
        ):
            continue
        sign = compare(value, sp.S.Zero)
        if (
            (relation == "positive" and sign <= 0)
            or (relation == "nonzero" and sign == 0)
            or (relation == "nonnegative" and sign < 0)
        ):
            return expression, relation, value
    return None


def case_failed(compiled, q, log_case):
    rejection = failed(compiled, q)
    data = compiled.log_product
    if rejection is None and data is not None and data.log_first and not log_case:
        expression = data.argument - 1
        value = sp.simplify(
            expression.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})
        )
        if value == 0:
            return expression, "nonzero", value
    return rejection


def ratio_factor(value):
    value = sp.cancel(value)
    if sp.fraction(value)[1].has(C):
        ratio = sp.cancel(value.subs(S, T * C))
        if ratio.free_symbols == {T}:
            return ratio
    if sp.fraction(value)[1].has(S):
        ratio = sp.cancel(value.subs(C, U * S))
        if ratio.free_symbols == {U}:
            return ratio
    return sp.fraction(value)[0]


def branches(compiled, preferred, allow_inverse=False):
    from .exam_trigonometric_finite_log import data_of
    from .exam_trigonometric_radical_product import factor_branches

    data = compiled.log_product
    if data_of(compiled) is not None:
        # Physical x domains must be checked on finite translates, not residues.
        from .exam_trigonometric_finite_log import branches as finite_branches

        return finite_branches(compiled, preferred, allow_inverse)
    result = []
    for log_case, factor in zero_cases(data):
        if data.equality is not None and data.equality.linear is not None:
            from .exam_trigonometric_log_linear import branches as linear_branches

            source = linear_branches(compiled, preferred, allow_inverse)
        else:
            source = factor_branches(factor, preferred, allow_inverse)
        for b in source:
            residues = tuple(
                q for q in b.residues if case_failed(compiled, q, log_case) is None
            )
            result.append(replace(b, residues=residues))
    if data.equality is not None:
        from .exam_trigonometric_log_equality import order_branches

        return order_branches(data.equality, result)
    return tuple(result)


def zero_cases(data):
    if data.equality is not None:
        return ((False, sp.cancel(data.factor / data.divide)),)
    if data.radical is not None and data.radical.divide:
        return ((True, ratio_factor(data.argument - 1)),)
    cases = [(False, ratio_factor(data.factor / data.divide))]
    if data.argument is not None and data.nonzero_bound is None:
        cases.append((True, ratio_factor(data.argument - 1)))
    return tuple(reversed(cases)) if data.log_first else tuple(cases)


def prepare(compiled, parent_html):
    from .exam_trigonometric_log_methods import prepare as reviewed

    return reviewed(compiled, parent_html)


def series(compiled, branches, residues):
    from .exam_trigonometric_inverse import centred
    from .exam_trigonometric_selection import periodic, restricted_series

    equality = (
        compiled.log_product.equality if compiled.log_product is not None else None
    )
    identity = equality.identity if equality is not None else None
    if identity is not None:
        if identity.finite_base is not None:
            return identity.finite_base.series()
        if identity.base_change is not None:
            return periodic(residues)
    result = tuple(dict.fromkeys(s for b in branches for s in restricted_series(b)))
    if equality is not None and equality.centre_inverse:
        result = tuple(s for item in result for s in centred((item,)))
    return result
