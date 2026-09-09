"""Deterministic planners for two parent-approved rational-expression forms."""

from __future__ import annotations

from fractions import Fraction
from math import gcd, isqrt
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_SQUARE_DIFFERENCE = re.compile(
    r"^\((?P<left>\d+)\^\{2\}-(?P<right>\d+)\^\{2\}\)\\colon(?P<divisor>\d+)$"
)
_FRACTION_DIVISION = re.compile(
    r"^(?:(?P<whole>\d+)\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}"
    r"|\\frac\{(?P<first_numerator>\d+)\}\{(?P<first_denominator>\d+)\})"
    r"(?P<operation>\\colon|\\cdot)\\frac\{(?P<divisor_numerator>\d+)\}\{(?P<divisor_denominator>\d+)\}$"
)
_CONJUGATE_PRODUCT = re.compile(
    r"^\((?P<first>\\sqrt\{\d+\}|\d+)-(?P<second>\\sqrt\{\d+\}|\d+)\)"
    r"(?:\\cdot)?\((?P=first)\+(?P=second)\)$"
)
_RADICAL_FACTOR = re.compile(
    r"^\(\\sqrt\{(?P<left>\d+)\}(?P<sign>[+-])\\sqrt\{(?P<base>\d+)\}\)"
    r"(?:\\cdot)?\\sqrt\{(?P=base)\}$"
)


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain one formula")
    return (
        str(formulas[0].get("data-inline-latex") or "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\div", "\\colon")
        .replace(":", "\\colon")
        .replace(" ", "")
    )


def _fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _decimal(value: Fraction) -> str:
    remainder = value.denominator
    twos = fives = 0
    while remainder % 2 == 0:
        remainder //= 2
        twos += 1
    while remainder % 5 == 0:
        remainder //= 5
        fives += 1
    if remainder != 1:
        raise RightTrianglePlanError("result is not a terminating decimal")
    if value.denominator == 1:
        return str(value.numerator)
    digits = max(twos, fives)
    scaled = abs(value.numerator) * 10**digits // value.denominator
    rendered = str(scaled).zfill(digits + 1)
    return f"{'-' if value < 0 else ''}{rendered[:-digits]},{rendered[-digits:]}"


def _finish(value: Fraction) -> tuple[str, ...]:
    """Keep the ordinary fraction and explicitly show its decimal form."""

    if value.denominator == 1:
        return (str(value.numerator),)
    decimal = _decimal(value)
    digits = len(decimal.removeprefix("-").split(",", 1)[1])
    scale = 10**digits // value.denominator
    numerator = value.numerator * scale
    return (_fraction(value), f"\\frac{{{numerator}}}{{{10**digits}}}", decimal.replace(",", "{,}"))


def _plan(context: dict[str, Any], *, formula_pattern: re.Pattern[str], calculation: Any) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("numeric expression conditions must be text-only")
    formula = _formula(condition)
    match = formula_pattern.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match the registered expression form")
    steps, result = calculation(formula, match)
    answer = _decimal(result)
    calculation_html = "=".join((*steps, *_finish(result)))
    html = (
        '<p>Вы­пол­ним пре­об­ра­зо­ва­ния:</p><center><p>'
        f'<span data-inline-latex="{calculation_html}"></span>.</p></center>'
    )
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))


def build_square_difference_plan(context: dict[str, Any]) -> RepairPlan:
    """Use the difference-of-squares identity before division."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        left, right, divisor = (int(match[name]) for name in ("left", "right", "divisor"))
        difference, total = left - right, left + right
        result = Fraction(difference * total, divisor)
        return (
            formula,
            f"\\frac{{({left}-{right})({left}+{right})}}{{{divisor}}}",
            f"\\frac{{{difference}\\cdot{total}}}{{{divisor}}}",
        ), result

    return _plan(context, formula_pattern=_SQUARE_DIFFERENCE, calculation=calculation)


def build_fraction_division_plan(context: dict[str, Any]) -> RepairPlan:
    """Convert a mixed number if needed, reverse the divisor, then cancel."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        divisor_numerator = int(match["divisor_numerator"])
        divisor_denominator = int(match["divisor_denominator"])
        if match["whole"] is None:
            first = Fraction(int(match["first_numerator"]), int(match["first_denominator"]))
        else:
            whole, numerator, denominator = (int(match[name]) for name in ("whole", "numerator", "denominator"))
            first = Fraction(whole * denominator + numerator, denominator)
        second = Fraction(divisor_numerator, divisor_denominator)
        result = first / second if match["operation"] == "\\colon" else first * second
        left_numerator, left_denominator = first.numerator, first.denominator
        right_numerator, right_denominator = second.denominator, second.numerator
        if match["operation"] == "\\colon":
            right_numerator, right_denominator = second.denominator, second.numerator
        else:
            right_numerator, right_denominator = second.numerator, second.denominator
        divisor = gcd(left_numerator, right_denominator)
        left_numerator //= divisor
        right_denominator //= divisor
        divisor = gcd(right_numerator, left_denominator)
        right_numerator //= divisor
        left_denominator //= divisor
        return (
            formula,
            f"\\frac{{{first.numerator}}}{{{first.denominator}}}\\cdot\\frac{{{second.denominator}}}{{{second.numerator}}}",
            f"\\frac{{{left_numerator}}}{{{left_denominator}}}\\cdot\\frac{{{right_numerator}}}{{{right_denominator}}}",
            f"\\frac{{{left_numerator}\\cdot{right_numerator}}}{{{left_denominator}\\cdot{right_denominator}}}",
        ), result

    return _plan(context, formula_pattern=_FRACTION_DIVISION, calculation=calculation)


def _squared_value(token: str) -> int:
    radical = re.fullmatch(r"\\sqrt\{(?P<value>\d+)\}", token)
    if radical:
        return int(radical["value"])
    value = int(token)
    return value * value


def _squared_latex(token: str) -> str:
    return f"({token})^{{2}}" if token.startswith("\\sqrt") else f"{token}^{{2}}"


def build_conjugate_product_plan(context: dict[str, Any]) -> RepairPlan:
    """Apply the difference-of-squares formula to matching radical conjugates."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is not None and _RADICAL_FACTOR.fullmatch(_formula(condition)):
        return build_radical_factor_plan(context)

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        first, second = match["first"], match["second"]
        first_value, second_value = _squared_value(first), _squared_value(second)
        return (
            formula,
            f"{_squared_latex(first)}-{_squared_latex(second)}",
            f"{first_value}-{second_value}",
        ), Fraction(first_value - second_value)

    return _plan(context, formula_pattern=_CONJUGATE_PRODUCT, calculation=calculation)


def build_radical_factor_plan(context: dict[str, Any]) -> RepairPlan:
    """Simplify a radical multiple before multiplying by the shared radical."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        left, base = int(match["left"]), int(match["base"])
        if left % base:
            raise RightTrianglePlanError("radicals do not have a shared square-free factor")
        coefficient = isqrt(left // base)
        if coefficient * coefficient * base != left:
            raise RightTrianglePlanError("first radical cannot be simplified to the shared radical")
        signed_coefficient = coefficient + (1 if match["sign"] == "+" else -1)
        if signed_coefficient == 0:
            middle = "0"
        elif signed_coefficient == 1:
            middle = f"\\sqrt{{{base}}}"
        elif signed_coefficient == -1:
            middle = f"-\\sqrt{{{base}}}"
        else:
            middle = f"{signed_coefficient}\\sqrt{{{base}}}"
        return (
            formula,
            f"({coefficient}\\sqrt{{{base}}}{match['sign']}\\sqrt{{{base}}})\\cdot\\sqrt{{{base}}}",
            f"{middle}\\cdot\\sqrt{{{base}}}",
            f"{signed_coefficient}\\cdot{base}",
        ), Fraction(signed_coefficient * base)

    return _plan(context, formula_pattern=_RADICAL_FACTOR, calculation=calculation)
