"""Planner for ratios of products of decimal factors."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_DECIMAL = r"\d+(?:\{,\}\d+)?"
_RATIO = re.compile(
    rf"^\\frac\{{(?P<numerator>{_DECIMAL}(?:\\cdot{_DECIMAL})?)\}}"
    rf"\{{(?P<denominator>{_DECIMAL}(?:\\cdot{_DECIMAL})?)\}}$"
)
_SIMPLE_PRODUCT = re.compile(rf"^(?P<left>{_DECIMAL})\\cdot(?P<right>{_DECIMAL})$")


def _factors(raw: str) -> tuple[str, ...]:
    return tuple(raw.split("\\cdot"))


def _decimal_parts(raw: str) -> tuple[int, int]:
    whole, separator, fractional = raw.partition("{,}")
    return int(whole + fractional), len(fractional) if separator else 0


def _answer(value: Fraction) -> str:
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise RightTrianglePlanError("result is not a terminating decimal")
    if value.denominator == 1:
        return str(value.numerator)
    digits = max(twos, fives)
    raw = str(abs(value.numerator) * 10**digits // value.denominator).zfill(digits + 1)
    return f"{'-' if value < 0 else ''}{raw[:-digits]},{raw[-digits:]}"


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain one formula")
    formula = str(formulas[0].get("data-inline-latex") or "").replace(" ", "")
    if _RATIO.fullmatch(formula) is None:
        raise RightTrianglePlanError("condition does not match a decimal product ratio")
    return formula


def _simple_product_formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) > 1:
        raise RightTrianglePlanError("condition must contain one formula")
    formula = str(formulas[0].get("data-inline-latex") or "") if formulas else ""
    plain_text = not formula
    if not formula:
        match = re.search(r"\d+,\d+\s*·\s*\d+,\d+", soup.get_text(" ", strip=True))
        if match is None:
            raise RightTrianglePlanError("condition does not match a decimal product")
        formula = match.group(0).replace("·", "\\cdot")
    formula = re.sub(r"\s+", "", formula)
    if plain_text:
        formula = formula.replace(",", "{,}")
    if _SIMPLE_PRODUCT.fullmatch(formula) is None:
        raise RightTrianglePlanError("condition does not match a decimal product")
    return formula


def _joined(factors: tuple[int, ...]) -> str:
    return "\\cdot".join(str(value) for value in factors)


def _side(factors: tuple[int, ...], power: int) -> str:
    if power == 0:
        return _joined(factors)
    if len(factors) == 1:
        return str(factors[0] * 10**power)
    multiplier = "10" if power == 1 else f"10^{{{power}}}"
    return f"{_joined(factors)}\\cdot{multiplier}"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Move decimal separators into whole-number factors, then cancel exactly."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("decimal ratio conditions must be text-only")

    formula = _formula(condition)
    match = _RATIO.fullmatch(formula)
    assert match is not None
    numerator_parts = tuple(_decimal_parts(value) for value in _factors(match["numerator"]))
    denominator_parts = tuple(_decimal_parts(value) for value in _factors(match["denominator"]))
    numerator_values = tuple(value for value, _ in numerator_parts)
    denominator_values = tuple(value for value, _ in denominator_parts)
    numerator_digits = sum(digits for _, digits in numerator_parts)
    denominator_digits = sum(digits for _, digits in denominator_parts)
    numerator_product = 1
    denominator_product = 1
    for value in numerator_values:
        numerator_product *= value
    for value in denominator_values:
        denominator_product *= value
    result = Fraction(numerator_product * 10**denominator_digits, denominator_product * 10**numerator_digits)
    answer = _answer(result)

    scale = max(numerator_digits, denominator_digits)
    numerator_expanded = _side(numerator_values, denominator_digits)
    denominator_expanded = _side(denominator_values, numerator_digits)
    common_power = min(numerator_digits, denominator_digits)
    numerator_reduced = _side(numerator_values, denominator_digits - common_power)
    denominator_reduced = _side(denominator_values, numerator_digits - common_power)
    calculation = "=".join((
        formula,
        f"\\frac{{{numerator_expanded}}}{{{denominator_expanded}}}",
        f"\\frac{{{numerator_reduced}}}{{{denominator_reduced}}}",
        answer.replace(",", "{,}"),
    ))
    html = (
        f"<p>Умно­жим чис­ли­тель и зна­ме­на­тель на {10**scale}:</p>"
        f'<center><p><span data-inline-latex="{calculation}"></span>.</p></center>'
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


def build_simple_decimal_product_plan(context: dict[str, Any]) -> RepairPlan:
    """Use the group's parent wording for products of two decimal numbers."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("decimal product conditions must be text-only")
    formula = _simple_product_formula(condition)
    match = _SIMPLE_PRODUCT.fullmatch(formula)
    assert match is not None
    left_value, left_digits = _decimal_parts(match["left"])
    right_value, right_digits = _decimal_parts(match["right"])
    product = left_value * right_value
    digits = left_digits + right_digits
    answer = _answer(Fraction(product, 10**digits))
    changes: list[dict[str, Any]] = []
    if solution_section is None:
        left = match["left"].replace("{,}", ",")
        right = match["right"].replace("{,}", ",")
        solution = (
            f"<p>Умножим {left_value} на {right_value}, получим {product}. "
            "Отделим в произведении запятой справа столько десятичных знаков, "
            f"сколько их в обоих множителях, то есть {digits} знака, получим {answer}. "
            f"Следовательно, {left} · {right} = {answer}.</p>"
        )
        changes.append(_section_transformation(solution_section, "solution", "Решение", solution))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))
