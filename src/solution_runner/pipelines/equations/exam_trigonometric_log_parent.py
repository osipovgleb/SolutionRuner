"""Review explicit log-definition transitions and bounded parent TeX fractions."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_parser import Parser
from .power_arithmetic import clean


def small_fractions(text):
    return re.sub(
        r"\\frac([0-9])([0-9])(?![0-9])",
        lambda m: r"\frac{" + m[1] + "}{" + m[2] + "}",
        text,
    )


def definition_chain(formulas):
    from .exam_trigonometric_radical_equation import compile_values

    for formula in formulas:
        text = clean(small_fractions(formula))
        parts = re.split(r"\\(?:Leftrightarrow|iff)", text, maxsplit=3)
        if (
            len(parts) < 3
            or any(p.count("=") != 1 for p in parts[:3])
            or not re.search(r"\\(?:sin|cos)x\(", parts[2])
        ):
            continue
        atoms, denominators, logs = {}, [], []
        try:
            nodes = [
                Parser(p.replace("x", r"\alpha"), atoms, denominators, logs).parse()
                for part in parts[:3]
                for p in part.split("=")
            ]
            (argument, target, reduced, zero, factored, last), poles, _ = (
                compile_values([n.value for n in nodes], atoms, denominators)
            )
        except UnsupportedCondition:
            continue
        if (
            logs
            or poles
            or target.free_symbols
            or target.is_positive is not True
            or zero != 0
            or last != 0
            or not reduced.is_polynomial(S, C)
            or not 1 <= sp.Poly(reduced, S, C).total_degree() <= 2
            or argument.subs({S: 0, C: 0}) != target
        ):
            continue
        differences = (
            sp.expand(argument - target - reduced),
            sp.expand(reduced - factored),
        )
        if all(
            d.is_polynomial(S, C) and sp.rem(d, S * S + C * C - 1, S) == 0
            for d in differences
        ):
            return True
    return False
