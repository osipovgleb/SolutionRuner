"""Shared square-root factors, with the source's optional distributive method."""

import re
from dataclasses import replace
from fractions import Fraction
from math import isqrt

from ..core.numbers import parse_rational
from ..probability.common import UnsupportedCondition, line
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from .expression_repair import repair_terminal_product, with_condition_repair
from .numeric_special_forms import _formula, _plan, _prime_factors

_PATTERN = re.compile(
    r"\(\\sqrt\{(?P<left>[1-9]\d{0,5})\}(?P<sign>[+-])\\sqrt\{(?P<right>[1-9]\d{0,5})\}\)(?:\\cdot)?\\sqrt\{(?P<base>[1-9]\d{0,5})\}"
)


def _decompose(number):
    coefficient, tail = 1, 1
    for prime, count in _prime_factors(number).items():
        coefficient *= prime ** (count // 2)
        if count % 2:
            tail *= prime
    return coefficient, tail


def _calculation(formula, match):
    left, right, base = (int(match[k]) for k in ("left", "right", "base"))
    sign = match["sign"]
    direction = 1 if sign == "+" else -1
    a, ta = _decompose(left)
    b, tb = _decompose(right)
    c, tc = _decompose(base)
    if len({ta, tb, tc}) != 1:
        raise UnsupportedCondition("the three radicals need the same square-free part")
    if right == base and left % base == 0 and isqrt(left // base) ** 2 * base == left:
        coefficient = isqrt(left // base)
        signed = coefficient + direction
        middle = (
            "0"
            if signed == 0
            else (
                rf"\sqrt{{{base}}}"
                if signed == 1
                else (
                    rf"-\sqrt{{{base}}}"
                    if signed == -1
                    else rf"{signed}\sqrt{{{base}}}"
                )
            )
        )
        return (
            formula,
            rf"({coefficient}\sqrt{{{base}}}{sign}\sqrt{{{base}}})\cdot\sqrt{{{base}}}",
            middle + rf"\cdot\sqrt{{{base}}}",
            rf"{signed}\cdot{base}",
        ), Fraction(signed * base)
    answer = (a + direction * b) * c * ta
    return (
        formula,
        rf"({a}\sqrt{{{ta}}}{sign}{b}\sqrt{{{ta}}})\cdot{c}\sqrt{{{ta}}}",
        rf"({a}{sign}{b})\cdot{c}\cdot(\sqrt{{{ta}}})^2",
        rf"({a}{sign}{b})\cdot{c}\cdot{ta}",
    ), Fraction(answer)


def _two_methods(plan, context, formula, match):
    content = _normalized_content(context)
    section = _section(content, "solution")
    changes = list(plan.transformations)
    current = next(
        (
            t
            for t in changes
            if t["transformation_target_id"].startswith("section:solution")
        ),
        None,
    )
    first = current["value"]["html"] if current else section["html"]
    left, right, base = (int(match[k]) for k in ("left", "right", "base"))
    a, b = isqrt(left * base), isqrt(right * base)
    sign = match["sign"]
    if (
        a * a != left * base
        or b * b != right * base
        or Fraction(a + (b if sign == "+" else -b)) != parse_rational(plan.answer)
    ):
        raise UnsupportedCondition("the independent distributive calculation disagrees")
    html = "<p>Первый способ. Вынесем квадратные множители из-под корней:</p>" + first
    html += "<p>Второй способ. Раскроем скобки и перемножим корни:</p>" + line(
        formula + rf"=\sqrt{{{left * base}}}{sign}\sqrt{{{right * base}}}"
    )
    html += line(rf"{a}{sign}{b}={plan.answer}")
    if html == section["html"]:
        changes = [t for t in changes if t is not current]
    elif current:
        current["value"]["html"] = html
    else:
        changes.append(_section_transformation(section, "solution", "Решение", html))
    return replace(plan, transformations=tuple(changes))


def build_context_repair_plan(context, *, vertical_roots=False, two_methods=False):
    prepared, change = repair_terminal_product(context)
    plan = _plan(
        prepared,
        formula_pattern=_PATTERN,
        calculation=_calculation,
        vertical_roots=vertical_roots,
    )
    if two_methods:
        formula = _formula(_section(_normalized_content(prepared), "condition"))
        match = _PATTERN.fullmatch(formula)
        plan = _two_methods(plan, prepared, formula, match)
    return with_condition_repair(plan, change)
