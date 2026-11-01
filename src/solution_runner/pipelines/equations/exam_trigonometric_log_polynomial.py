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
from .power_arithmetic import clean

L = sp.Symbol("l", real=True)

if TYPE_CHECKING:
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


def compile_polynomial(formula, parent_html):
    from .exam_trigonometric_log_parser import Parser
    from .exam_trigonometric_log_polynomial_style import review
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if text.count("=") != 1 or not text.endswith("=0"):
        raise UnsupportedCondition(
            "one complete zero log-polynomial equality is required"
        )
    atoms, denominators, logs = {}, [], []
    node = Parser(text[:-2].replace("x", r"\alpha"), atoms, denominators, logs).parse()
    value = node.value
    if not logs:
        return None
    symbols = tuple(e[0] for e in logs)
    values, poles, identities = compile_values(
        [value, *(e[2] for e in logs)], atoms, denominators, extra_symbols=symbols
    )
    value, *arguments = values
    if len({(e[1], arg) for e, arg in zip(logs, arguments, strict=True)}) != 1:
        return None
    value = sp.cancel(value.subs(dict.fromkeys(symbols, L)))
    num, den = sp.fraction(value)
    if den.has(L) or num.free_symbols - {L} or not num.is_polynomial(L):
        return None
    if any(p.has(*symbols) for p in poles):
        return None
    if not 1 <= sp.degree(num, L) <= 2:
        raise UnsupportedCondition(
            "a linear or quadratic polynomial in one log is required"
        )
    argument = arguments[0]
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
    if not levels or any(
        v.is_Rational is not True or abs(v) > 20 or v.q > 12 for v in levels
    ):
        raise UnsupportedCondition("reviewed bounded rational log levels are required")
    base = logs[0][1]
    data, ascending = review(base, argument, num, levels, parent_html)
    levels = tuple(
        sorted(
            levels,
            key=cmp_to_key(
                lambda a, b: compare(sp.simplify(base**a), sp.simplify(base**b))
            ),
            reverse=not ascending,
        )
    )

    def log_text(node):
        if node.kind == "log":
            return node.text
        return next(
            (value for child in node.children if (value := log_text(child))), ""
        )

    source_argument = log_text(node).replace(r"\alpha", "x")
    source_argument = re.sub(
        r"\\(sin|cos|tg|ctg)(?=x)", lambda m: "\\" + m[1] + " ", source_argument
    )
    data = replace(data, levels=levels, argument_text=source_argument)
    raw = sp.expand(sp.prod(argument - base**v for v in levels))
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 4:
        raise UnsupportedCondition(
            "the log-level equations need a bounded polynomial certificate"
        )
    return Equation(raw, identities, sp.S.One, poles=poles, log_polynomial=data)


def branches(compiled, allow_inverse=False):
    from .exam_trigonometric_log_product import failed
    from .exam_trigonometric_radical_product import factor_branches

    data = compiled.log_polynomial
    result = []
    for level in data.levels:
        for b in factor_branches(
            sp.expand(data.argument - data.base**level), C, allow_inverse
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
