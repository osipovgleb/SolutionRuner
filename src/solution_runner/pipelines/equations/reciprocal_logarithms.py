"""Equal logarithms with reciprocal bases and affine arguments."""

from __future__ import annotations

import re
from fractions import Fraction

from solution_runner.pipelines.core.numbers import (
    exact_integer_root,
    format_answer,
    format_latex_fraction,
)

from .exponential_affine import _parse_base, _parse_linear
from .group_26656 import RepairPlan
from .group_26667_planner import _normalized_quadratic_formula

_BASE = r"(?:\d+(?:\{,\}\d+)?|\\frac\{[1-9]\d*\}\{[1-9]\d*\})"
_FORMULA = re.compile(
    rf"\\log_(?P<lb>\{{?\(?{_BASE}\)?\}}?)\s*\\frac\{{(?P<n>[^{{}}]+)\}}\{{(?P<d>[1-9]\d*)\}}="
    rf"\\log_(?P<rb>\{{?\(?{_BASE}\)?\}}?)\s*\((?P<right>[^{{}}]+)\)"
)


def _base(token: str) -> Fraction:
    if token.startswith("{") and token.endswith("}"):
        token = token[1:-1]
    value = _parse_base(token)
    if value <= 0 or value == 1:
        raise ValueError("logarithm base must be positive and different from one")
    return value


def build_reciprocal_plan(formula: str) -> RepairPlan | None:
    match = _FORMULA.fullmatch(formula)
    if match is None:
        return None
    left_base, right_base = _base(match["lb"]), _base(match["rb"])
    if left_base * right_base != 1:
        raise ValueError("logarithm bases must be reciprocal")
    numerator_constant, numerator_coefficient = _parse_linear(match["n"])
    right_constant, right_coefficient = _parse_linear(match["right"])
    denominator = int(match["d"])
    a = numerator_coefficient * right_coefficient
    b = numerator_coefficient * right_constant + numerator_constant * right_coefficient
    c = numerator_constant * right_constant - denominator
    if not a:
        raise ValueError(
            "reciprocal logarithm form requires two nonconstant affine arguments"
        )
    square_root = exact_integer_root(b * b - 4 * a * c, 2)
    roots = tuple(
        sorted({Fraction(-b - square_root, 2 * a), Fraction(-b + square_root, 2 * a)})
    )
    admissible = [
        x
        for x in roots
        if numerator_constant + numerator_coefficient * x > 0
        and right_constant + right_coefficient * x > 0
    ]
    if len(admissible) != 1:
        raise ValueError("reciprocal logarithms require exactly one admissible root")
    value = admissible[0]
    base = (
        str(left_base.numerator)
        if left_base.denominator == 1 and left_base < 10
        else "{" + format_latex_fraction(left_base) + "}"
    )
    left = f"\\frac{{{match['n']}}}{{{denominator}}}"
    right = match["right"]
    domain = f"{left}>0\\\\{right}>0"
    root_set = r"\\".join(f"x={format_latex_fraction(x)}" for x in roots)
    steps = (
        formula,
        f"\\log_{base}{left}=-\\log_{base}({right})",
        f"\\log_{base}{left}=\\log_{base}\\frac{{1}}{{{right}}}",
        f"\\begin{{cases}}{left}=\\frac{{1}}{{{right}}}\\\\{domain}\\end{{cases}}",
        f"\\begin{{cases}}({match['n']})({right})={denominator}\\\\{domain}\\end{{cases}}",
        f"\\begin{{cases}}{_normalized_quadratic_formula(a, b, c)}\\\\{domain}\\end{{cases}}",
        f"\\begin{{cases}}\\left[\\begin{{aligned}}{root_set}\\end{{aligned}}\\right.\\\\{domain}\\end{{cases}}",
        f"x={format_latex_fraction(value)}",
    )
    html = "<p>Приведём логарифмы к одному основанию. Основания взаимно обратны, поэтому логарифм правой части меняет знак:</p>"
    html += "".join(
        f'<center><p><span data-inline-latex="{step}"></span>.</p></center>'
        for step in steps[:3]
    )
    html += "<p>Приравняем аргументы и решим квадратное уравнение. Сохраним условия положительности обоих аргументов, чтобы исключить посторонние корни:</p>"
    html += "".join(
        f'<center><p><span data-inline-latex="{step}"></span>.</p></center>'
        for step in steps[3:]
    )
    return RepairPlan(
        answer=format_answer(value), condition_html="", solution_html=html
    )
