"""Fail-closed quadratic-root selector for source group 26667."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .solution_formatting import vertical_derivation

RULE = "elementary-equations-26667-quadratic-root-selector"
PARENT_PROBLEM_ID = "095f3b3a-83aa-429e-ab8d-8feceeb37f53"

_CONDITION = re.compile(
    r"(?:Найдите корень уравнения|Решите уравнение):? "
    r"(?P<a_sign>-?)(?P<a_value>\d*)x\^\{2\}"
    r"(?:(?P<b_sign>[+-])(?P<b_value>\d*)x)?"
    r"(?:(?P<c_sign>[+-])(?P<c_value>\d+))?=0\. "
    r"Если уравнение имеет (?:более|больше) одного корня, "
    r"(?:в ответе )?(?:укажите|запишите) "
    r"(?P<kind>меньший|больший) из них\."
)

_SHIFTED_CONDITION = re.compile(
    r"(?:Найдите корень уравнения|Решите уравнение) "
    r"(?P<formula>(?P<a_sign>-?)(?P<a_value>\d*)x\^\{2\}"
    r"(?P<b_sign>[+-])(?P<b_value>\d*)x="
    r"(?P<rhs_sign>-?)(?P<rhs_value>\d+))\. "
    r"Если уравнение имеет (?:более|больше) одного корня, "
    r"(?:в ответе )?(?:укажите|запишите) "
    r"(?P<kind>меньший|больший) из них\."
)

_TRANSPOSED_CONDITION = re.compile(
    r"(?:Найдите корень уравнения|Решите уравнение) "
    r"(?P<formula>(?P<a_sign>-?)(?P<a_value>\d*)x\^\{2\}"
    r"(?P<c_sign>[+-])(?P<c_value>\d+)="
    r"(?P<b_sign>-?)(?P<b_value>\d*)x)\. "
    r"Если уравнение имеет (?:более|больше) одного корня, "
    r"(?:в ответе )?(?:укажите|запишите) "
    r"(?P<kind>меньший|больший) из них\."
)

_RIGHT_AFFINE_CONDITION = re.compile(
    r"(?:Найдите корень уравнения|Решите уравнение):? "
    r"(?P<formula>(?P<a_sign>-?)(?P<a_value>\d*)x\^\{2\}="
    r"(?P<b_sign>-?)(?P<b_value>\d*)x"
    r"(?P<c_sign>[+-])(?P<c_value>\d+))\. "
    r"Если уравнение имеет (?:более|больше) одного корня, "
    r"(?:в ответе )?(?:укажите|запишите) "
    r"(?P<kind>меньший|больший) из них\."
)


def _coefficient(sign: str | None, value: str | None, *, default: int) -> int:
    if sign is None:
        return default
    magnitude = int(value or "1")
    return -magnitude if sign == "-" else magnitude


def _number(value: Fraction) -> str:
    """Render an integer or a terminating decimal with the Russian comma."""
    if value.denominator == 1:
        return str(value.numerator)
    reduced_denominator = value.denominator
    while reduced_denominator % 2 == 0:
        reduced_denominator //= 2
    while reduced_denominator % 5 == 0:
        reduced_denominator //= 5
    if reduced_denominator != 1:
        raise RightTrianglePlanError("root has an infinite decimal representation")
    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    denominator = value.denominator
    places = 0
    while denominator > 1:
        denominator = denominator // 2 if denominator % 2 == 0 else denominator // 5
        places += 1
    digits = str(numerator * 10**places // value.denominator).zfill(places + 1)
    return f"{sign}{digits[:-places]},{digits[-places:]}"


def _latex_number(value: int, *, squared: bool = False) -> str:
    text = str(value)
    if value < 0:
        text = f"({text})"
    return f"{text}^{{2}}" if squared else text


def _normalized_quadratic_formula(a: int, b: int, c: int) -> str:
    """Render ``ax² + bx + c = 0`` without changing the accepted grammar."""

    leading = "x^{2}" if a == 1 else "-x^{2}" if a == -1 else f"{a}x^{{2}}"
    b_term = (
        "+x" if b == 1 else "-x" if b == -1 else f"+{b}x" if b > 0 else f"-{abs(b)}x"
    )
    c_term = f"+{c}" if c > 0 else f"-{abs(c)}"
    return f"{leading}{b_term}{c_term}=0"


def _solution_html(
    formula: str, a: int, b: int, c: int, roots: list[Fraction], normalize: bool
) -> str:
    discriminant = b * b - 4 * a * c
    normalization_html = ""
    equation_steps = formula
    if normalize:
        normalized_formula = _normalized_quadratic_formula(a, b, c)
        normalization_html = (
            "<p>Перенесём число из правой части в левую часть уравнения:</p>"
            f'<center><p><span data-inline-latex="{formula}\\iff {normalized_formula}"></span>.</p></center>'
        )
        equation_steps = normalized_formula
    numerator, denominator = str(-b), str(2 * a)
    four_ac = 4 * a * c
    root_radicand = f"{b * b}{'-' if four_ac >= 0 else '+'}{abs(four_ac)}"
    root_rows = "\\\\".join(
        f"x=\\frac{{{numerator}{'+' if sign > 0 else '-'}\\sqrt{{{root_radicand}}}}}{{{denominator}}}"
        for sign in (1, -1)
    )
    value_rows = "\\\\".join(
        f"x={_number(value).replace(',', '{,}')}" for value in (roots[1], roots[0])
    )
    discriminant_substitution = f"{_latex_number(b, squared=True)}-4\\cdot{_latex_number(a)}\\cdot{_latex_number(c)}"
    expected_solution = vertical_derivation(
        normalization_html + "<p>Вос­поль­зу­ем­ся фор­му­лой дис­кри­ми­нан­та:</p>"
        f'<center><p><span data-inline-latex="D=b^2-4ac={discriminant_substitution}={discriminant}"></span>.</p></center>'
        "<p>Вос­поль­зу­ем­ся фор­му­лой для кор­ней квад­рат­но­го урав­не­ния:</p>"
        f'<center><p><span data-inline-latex="{equation_steps}\\iff \\left[\\begin{{aligned}}{root_rows}\\end{{aligned}}\\right.\\iff \\left[\\begin{{aligned}}{value_rows}\\end{{aligned}}\\right."></span>.</p></center>'
    )
    return expected_solution


def _condition_parts(condition_html: str) -> tuple[str, re.Match[str], str]:
    soup = BeautifulSoup(condition_html, "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text(strip=True):
        raise RightTrianglePlanError("condition formula is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    spans[0].replace_with(formula)
    condition_text = re.sub(
        r"\s+([.])",
        r"\1",
        " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()),
    )
    for kind, pattern in (
        ("standard", _CONDITION),
        ("shifted", _SHIFTED_CONDITION),
        ("transposed", _TRANSPOSED_CONDITION),
        ("right-affine", _RIGHT_AFFINE_CONDITION),
    ):
        match = pattern.fullmatch(condition_text)
        if match is not None:
            return formula, match, kind
    raise RightTrianglePlanError("condition does not match a supported quadratic")


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 26667 must not have assets")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if (
        condition is None
        or content.get("assets")
        or tuple(condition.get("asset_keys") or ())
    ):
        raise RightTrianglePlanError("condition is incomplete")
    formula, match, kind = _condition_parts(str(condition.get("html") or ""))
    a = _coefficient(match.group("a_sign"), match.group("a_value"), default=1)
    if kind == "standard":
        b = _coefficient(match.group("b_sign"), match.group("b_value"), default=0)
        c = _coefficient(match.group("c_sign"), match.group("c_value"), default=0)
    elif kind == "shifted":
        b = _coefficient(match.group("b_sign"), match.group("b_value"), default=0)
        c = -_coefficient(match.group("rhs_sign"), match.group("rhs_value"), default=0)
    elif kind == "transposed":
        b = -_coefficient(match.group("b_sign"), match.group("b_value"), default=1)
        c = _coefficient(match.group("c_sign"), match.group("c_value"), default=0)
    else:
        b = -_coefficient(
            match.group("b_sign") or "+", match.group("b_value"), default=1
        )
        c = -_coefficient(match.group("c_sign"), match.group("c_value"), default=0)
    if a == 0:
        raise RightTrianglePlanError("quadratic coefficient is zero")
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        raise RightTrianglePlanError("quadratic has no real roots")
    square_root = math.isqrt(discriminant)
    if square_root * square_root != discriminant:
        raise RightTrianglePlanError("discriminant is not a nonnegative square")
    roots = sorted(
        (Fraction(-b - square_root, 2 * a), Fraction(-b + square_root, 2 * a))
    )
    chosen = roots[0] if match.group("kind") == "меньший" else roots[-1]
    expected_solution = _solution_html(
        formula,
        a,
        b,
        c,
        roots,
        kind != "standard",
    )
    changes = []
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(
            _section_transformation(solution, "solution", "Решение", expected_solution)
        )
    actual_answer = (
        BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser")
        .get_text("", strip=True)
        .replace(" ", "")
    )
    canonical_answer = _number(chosen)
    if actual_answer != canonical_answer:
        changes.append(
            _section_transformation(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{canonical_answer}</span></p>',
            )
        )
    return RepairPlan(answer=canonical_answer, transformations=tuple(changes))
