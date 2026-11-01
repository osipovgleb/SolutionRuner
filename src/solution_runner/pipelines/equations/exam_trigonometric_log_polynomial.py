"""Reduce one fixed-base log polynomial, retaining every original trig denominator."""

import re
from dataclasses import dataclass, replace
from functools import cmp_to_key
from typing import TYPE_CHECKING

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S

L = sp.Symbol("l", real=True)

if TYPE_CHECKING:
    from .exam_trigonometric_log_common import CommonLogs
    from .exam_trigonometric_log_powers import LogPowers


@dataclass(frozen=True)
class LogPolynomial:
    base: sp.Expr
    argument: sp.Expr
    polynomial: sp.Expr
    levels: tuple
    substitution: str | None
    trig_substitution: str | None
    factor_before: bool = False
    discriminant: bool = False
    alternative_selection: bool = False
    argument_text: str = ""
    powers: "LogPowers | None" = None
    normalization: "CommonLogs | None" = None


def compile_polynomial(formula, parent_html):
    from .exam_trigonometric_log_common import (
        argument_text,
        bounded_level,
        exact_power,
        normalize,
        parse_expression,
    )
    from .exam_trigonometric_log_polynomial_style import review
    from .exam_trigonometric_methods import Equation

    parsed = parse_expression(formula)
    if parsed is None:
        return None
    nodes, logs, constants, (values, poles, identities), cancelled = parsed
    symbols = tuple(e[0] for e in logs)
    value, *arguments = values
    if any(p.has(*symbols) for p in poles):
        return None
    normalized = normalize(value, logs, arguments, constants, parent_html)
    if normalized is None:
        return None
    base, argument, normalized_value, normalization = normalized
    if normalization is not None:
        normalization = replace(
            normalization,
            cancelled=cancelled,
        )
    value = normalized_value
    num, den = sp.fraction(value)
    if den.has(L) or num.free_symbols - {L} or not num.is_polynomial(L):
        return None
    if normalization is not None and normalization.constants:
        num = sp.expand(value)
    if not 1 <= sp.degree(num, L) <= 2:
        raise UnsupportedCondition(
            "a linear or quadratic polynomial in one log is required"
        )
    if (
        argument.free_symbols - {S, C}
        or not argument.is_polynomial(S, C)
        or not 1 <= sp.Poly(argument, S, C).total_degree() <= 2
    ):
        raise UnsupportedCondition(
            "a nonconstant unit-circle log argument of degree at most two is required"
        )
    if not sp.rem(argument, S * S + C * C - 1, S).free_symbols:
        raise UnsupportedCondition(
            "a constant circle argument requires a complete-domain method"
        )
    for pole in poles:
        if not pole.is_polynomial(S, C) or sp.Poly(pole, S, C).total_degree() > 2:
            raise UnsupportedCondition(
                "bounded original trigonometric poles are required"
            )
    levels = roots(num.subs(L, X))
    if not levels or any(not bounded_level(base, level) for level in levels):
        raise UnsupportedCondition("reviewed bounded exact log levels are required")
    data, ascending = review(base, argument, num, levels, parent_html)
    levels = tuple(
        sorted(
            levels,
            key=cmp_to_key(
                lambda a, b: compare(exact_power(base, a), exact_power(base, b))
            ),
            reverse=not ascending,
        )
    )

    source_argument = argument_text(nodes, logs, arguments, argument).replace(
        r"\alpha", "x"
    )
    source_argument = re.sub(
        r"\\(sin|cos|tg|ctg)(?=x)", lambda m: "\\" + m[1] + " ", source_argument
    )
    data = replace(
        data, levels=levels, argument_text=source_argument, normalization=normalization
    )
    raw = sp.expand(sp.prod(argument - exact_power(base, v) for v in levels))
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 4:
        raise UnsupportedCondition(
            "the log-level equations need a bounded polynomial certificate"
        )
    return Equation(raw, identities, sp.S.One, poles=poles, log_polynomial=data)


def branches(compiled, allow_inverse=False):
    from .exam_trigonometric_log_common import exact_power
    from .exam_trigonometric_log_product import failed
    from .exam_trigonometric_radical_product import factor_branches

    data = compiled.log_polynomial
    result = []
    for level in data.levels:
        for b in factor_branches(
            sp.expand(data.argument - exact_power(data.base, level)), C, allow_inverse
        ):
            result.append(
                replace(
                    b,
                    residues=tuple(
                        q for q in b.residues if failed(compiled, q) is None
                    ),
                )
            )
    return tuple(result)
