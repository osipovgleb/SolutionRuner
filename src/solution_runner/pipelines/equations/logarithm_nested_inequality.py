"""Normalize nested logarithms, then reuse the exact quadratic-log inverse solver."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm, read_equation
from .logarithm_quadratic_inequality import solve_quadratic
from .power_arithmetic import clean
from .rational_inequality import OPERATORS, set_latex
from .rational_inequality_parser import X


@dataclass(frozen=True)
class NestedLogarithm:
    inner_base: sp.Expr
    original_outer_base: sp.Expr
    quadratic: object
    solution: object

    def endpoint(self, value):
        for level in (self.quadratic.solution.start, self.quadratic.solution.end):
            if value == self.inner_base**level:
                return (
                    sp.latex(value)
                    if value.is_Rational
                    else sp.latex(
                        sp.Pow(self.inner_base, level, evaluate=False),
                        root_notation=True,
                    )
                )
        raise UnsupportedCondition(
            "the endpoint needs its exact reviewed logarithm level"
        )

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def inner_logarithms(text):
    inner = []
    for match in re.finditer(r"\\log_", text):
        try:
            atom, power, end = logarithm(text, match.start(), X, extended=True)
        except UnsupportedCondition:
            continue
        if atom.argument == X and not atom.root and not atom.denominator:
            inner.append((match.start(), end, atom.base, power))
    if len(inner) != 2 or tuple(row[3] for row in inner) != (1, 2):
        raise UnsupportedCondition("one inner logarithm and its square are required")
    base = inner[0][2]
    if base.is_Rational is not True or base <= 1 or inner[1][2] != base:
        raise UnsupportedCondition(
            "both complete inner logarithms need the same increasing rational base"
        )
    normalized, remainder = text, text
    for start, end, _, power in reversed(inner):
        normalized = (
            normalized[:start] + ("x" if power == 1 else "x^2") + normalized[end:]
        )
        remainder = remainder[:start] + remainder[end:]
    if "x" in remainder:
        raise UnsupportedCondition(
            "the original variable may occur only inside the complete inner logarithms"
        )
    return base, normalized


def analyze(formula):
    inner_base, normalized = inner_logarithms(clean(formula))
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", normalized)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one complete nested logarithm inequality is required"
        )
    atoms, expression = read_equation(parts[0] + "=" + parts[2], extended=True)
    if len(atoms) != 2 or tuple(a.argument for a in atoms) != (-X, X**2):
        raise UnsupportedCondition(
            "the outer arguments must be the negative inner logarithm and its square"
        )
    base = atoms[0].base
    if base.is_Rational is not True or any(
        a.base != base or a.root or a.denominator for a in atoms
    ):
        raise UnsupportedCondition(
            "two complete outer logarithms need the same constant rational base"
        )
    if expression.free_symbols - {a.symbol for a in atoms}:
        raise UnsupportedCondition(
            "the outer expression may depend only on the two logarithms"
        )
    canonical, scale = (base, 1) if base > 1 else (1 / base, -1)
    value = sp.expand(
        expression.subs({atoms[0].symbol: scale * X, atoms[1].symbol: 2 * scale * X})
    )
    quadratic = solve_quadratic(canonical, -X, value, OPERATORS[parts[1]])
    interval = quadratic.solution
    if not isinstance(interval, sp.Interval) or any(
        p.is_Rational is not True or max(abs(p.p), p.q) > 256
        for p in (interval.start, interval.end)
    ):
        raise UnsupportedCondition(
            "this nested parent needs a bounded rational inner-logarithm interval"
        )
    solution = sp.Interval(
        inner_base**interval.start,
        inner_base**interval.end,
        left_open=interval.left_open,
        right_open=interval.right_open,
    )
    return NestedLogarithm(inner_base, base, quadratic, solution)
