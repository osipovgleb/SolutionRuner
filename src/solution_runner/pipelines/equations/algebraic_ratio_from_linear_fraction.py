"""Plans for finding ``a / b`` from a linear fractional equality."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_CONDITION = re.compile(r"^\\frac\{(?P<numerator>[^{}]+)\}\{(?P<denominator>[^{}]+)\}=(?P<value>-?\d+)$")
_LINEAR = re.compile(
    r"^(?P<first_coefficient>\d*)(?P<first_variable>[ab])"
    r"(?P<sign>[+-])(?P<second_coefficient>\d*)(?P<second_variable>[ab])$"
)


def _coefficient(value: str) -> int:
    return int(value or "1")


def _term(coefficient: int, variable: str) -> str:
    if coefficient == 1:
        return variable
    return f"{coefficient}{variable}"


def _join(first: str, sign: str, second: str) -> str:
    return f"{first}{sign}{second}"


def _linear_coefficients(expression: str) -> tuple[int, int]:
    match = _LINEAR.fullmatch(expression)
    if match is None or match["first_variable"] == match["second_variable"]:
        raise RightTrianglePlanError("linear expression must contain one a and one b term")
    first = _coefficient(match["first_coefficient"])
    second = _coefficient(match["second_coefficient"])
    if match["sign"] == "-":
        second = -second
    values = {match["first_variable"]: first, match["second_variable"]: second}
    return values["a"], values["b"]


def _signed_term(coefficient: int, variable: str = "") -> str:
    term = _term(abs(coefficient), variable) if variable else str(abs(coefficient))
    return term if coefficient >= 0 else f"-{term}"


def _fraction_latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    prefix = "-" if value < 0 else ""
    return f"{prefix}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _finite_decimal(value: Fraction) -> str | None:
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        return None
    places = max(twos, fives)
    scale = 10**places // value.denominator
    numerator = abs(value.numerator) * scale
    digits = str(numerator).zfill(places + 1)
    sign = "-" if value < 0 else ""
    return f"{sign}{digits[:-places]},{digits[-places:]}" if places else f"{sign}{digits}"


def _answer_latex(value: Fraction) -> tuple[str, str]:
    fraction = _fraction_latex(value)
    decimal = _finite_decimal(value)
    if decimal is None or value.denominator == 1:
        return fraction, decimal or str(value)
    return f"{fraction}={decimal.replace(',', '{,}')}", decimal


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 2 or str(formulas[0].get("data-inline-latex")) != r"\frac{a}{b}":
        raise RightTrianglePlanError("condition must ask for a / b and contain one equality")
    return str(formulas[1].get("data-inline-latex") or "").replace(" ", "")


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build two equivalent, fully deterministic derivations for this form only."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("linear ratio condition must be text-only")
    formula = _formula(condition)
    match = _CONDITION.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match a registered linear ratio form")

    numerator, denominator = match["numerator"], match["denominator"]
    numerator_a, numerator_b = _linear_coefficients(numerator)
    denominator_a, denominator_b = _linear_coefficients(denominator)
    value = int(match["value"])
    coefficient_a = numerator_a - value * denominator_a
    coefficient_b = value * denominator_b - numerator_b
    if coefficient_a == 0:
        raise RightTrianglePlanError("equality does not determine a / b")
    ratio = Fraction(coefficient_b, coefficient_a)
    ratio_latex, answer = _answer_latex(ratio)
    ratio_fraction = _fraction_latex(ratio)
    ratio_times_b = (
        "b" if ratio == 1 else "-b" if ratio == -1 else f"({ratio_fraction})b"
    )
    expressed_a = "b" if ratio == 1 else "-b" if ratio == -1 else f"{ratio_fraction}b"

    left = _signed_term(coefficient_a, "a")
    right_linear = _signed_term(coefficient_b, "b")
    primary = (
        f"{formula}\\iff {numerator}={value}({denominator})"
        f"\\iff {left}={right_linear}"
        f"\\iff a={expressed_a}"
        f"\\iff \\frac{{a}}{{b}}=\\frac{{{ratio_times_b}}}{{b}}={ratio_latex}"
    )

    html = f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
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
