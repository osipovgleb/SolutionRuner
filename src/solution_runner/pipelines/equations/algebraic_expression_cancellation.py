"""Deterministic plans for algebraic expressions whose variable cancels."""

from __future__ import annotations

from math import isqrt
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_COMMON_FACTOR = re.compile(
    r"^\\frac\{\((?P<factor>\d+)a\)\^\{2\}(?P<sign>[+-])(?P=factor)a\}"
    r"\{(?P=factor)a\^\{2\}(?P=sign)a\}$"
)
_RECIPROCAL_DIFFERENCE = re.compile(
    r"^\((?P<square>\d*)a\^(?:\{2\}|2)-(?P<term_square>\d+)\)\\cdot"
    r"\(\\frac\{1\}\{(?P<base>\d*)a(?P<first>[+-])(?P<term>\d+)\}"
    r"-\\frac\{1\}\{(?P=base)a(?P<second>[+-])(?P=term)\}\)$"
)
_DIFFERENCE_OVER_FACTOR = re.compile(
    r"^\\frac\{(?P<coefficient_square>\d*)x\^\{2\}-(?P<term_square>\d+)\}"
    r"\{(?P<coefficient>\d*)x(?P<sign>[+-])(?P<term>\d+)\}"
    r"-(?P=coefficient)x$"
)
_CONJUGATE_PRODUCT_MINUS_SQUARE = re.compile(
    r"^\((?P<coefficient>\d*)x(?P<first_sign>[+-])(?P<term>\d+)\)"
    r"\((?P=coefficient)x(?P<second_sign>[+-])(?P=term)\)"
    r"-(?P<square>\d*)x\^\{2\}$"
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
        .replace(" ", "")
    )


def _substitute_one(formula: str) -> str:
    """Replace variable occurrences without corrupting LaTeX command names."""

    return re.sub(r"(?<![A-Za-z])a(?![A-Za-z])", r"\\cdot 1", formula)


def _solution_html(
    primary: str,
    alternative: str,
    *,
    variable: str = "a",
    alternative_intro: str | None = None,
) -> str:
    """Return only section body markup; the content runtime owns the wrapper."""

    intro = alternative_intro or (
        "Поэтому подставим единицу вместо переменной: "
    )
    return (
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p><b>Приведем другое решение</b></p>'
        '<p>Так как это задание первой части, переменной '
        f'<span data-inline-latex="{variable}"></span> в ответе быть не может, значит, '
        f'она должна сократиться. {intro}</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
    )


def _plan(
    context: dict[str, Any], *, answer: int, primary: str, alternative: str, variable: str = "a",
    alternative_intro: str | None = None,
) -> RepairPlan:
    content = _normalized_content(context)
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    answer_text = str(answer)
    html = _solution_html(
        primary, alternative, variable=variable, alternative_intro=alternative_intro
    )
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer_text:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer_text}</span></p>'
        ))
    return RepairPlan(answer=answer_text, transformations=tuple(changes))


def _common_factor_plan(formula: str, match: re.Match[str], context: dict[str, Any]) -> RepairPlan:
    factor, sign = int(match["factor"]), match["sign"]
    primary = f"{formula}=\\frac{{{factor}a({factor}a{sign}1)}}{{a({factor}a{sign}1)}}={factor}"
    numerator = factor**2 + (factor if sign == "+" else -factor)
    denominator = factor + (1 if sign == "+" else -1)
    alternative = (
        f"{_substitute_one(formula)}="
        f"\\frac{{{factor}^{{2}}{sign}{factor}}}{{{factor}{sign}1}}="
        f"\\frac{{{factor**2}{sign}{factor}}}{{{denominator}}}="
        f"\\frac{{{numerator}}}{{{denominator}}}={factor}"
    )
    return _plan(context, answer=factor, primary=primary, alternative=alternative)


def _reciprocal_difference_plan(formula: str, match: re.Match[str], context: dict[str, Any]) -> RepairPlan:
    square, term_square = int(match["square"] or "1"), int(match["term_square"])
    base, term = int(match["base"] or "1"), int(match["term"])
    if isqrt(square) != base or isqrt(term_square) != term:
        raise RightTrianglePlanError("denominators do not match the difference of squares")
    first_sign, second_sign = match["first"], match["second"]
    numerator = (term if second_sign == "+" else -term) - (term if first_sign == "+" else -term)
    answer = numerator
    substitution = max(5, term // base + 1)
    first_at_value = base * substitution + (term if first_sign == "+" else -term)
    second_at_value = base * substitution + (term if second_sign == "+" else -term)
    if first_at_value <= 0 or second_at_value <= 0:
        raise RightTrianglePlanError("selected substitution must keep denominators positive")
    numerator_at_value = square * substitution**2 - term_square
    if numerator_at_value <= 0:
        raise RightTrianglePlanError("selected substitution must keep the first factor positive")
    primary = (
        f"{formula}=({square}a^2-{term_square})\\cdot"
        f"\\frac{{{base}a{second_sign}{term}-{base}a{first_sign}{term}}}"
        f"{{{square}a^2-{term_square}}}={answer}"
    )
    alternative = (
        f"({square}\\cdot {substitution}^2-{term_square})\\cdot"
        f"\\left(\\frac{{1}}{{{base}\\cdot {substitution}{first_sign}{term}}}"
        f"-\\frac{{1}}{{{base}\\cdot {substitution}{second_sign}{term}}}\\right)="
        f"({square * substitution**2}-{term_square})\\cdot"
        f"\\left(\\frac{{1}}{{{first_at_value}}}-\\frac{{1}}{{{second_at_value}}}\\right)="
        f"{numerator_at_value}\\cdot\\frac{{{second_at_value}-{first_at_value}}}"
        f"{{{first_at_value}\\cdot {second_at_value}}}={numerator_at_value}\\cdot"
        f"\\frac{{{numerator}}}{{{first_at_value * second_at_value}}}={answer}"
    )
    return _plan(
        context,
        answer=answer,
        primary=primary,
        alternative=alternative,
        alternative_intro=(
            f"Подставим, например, {substitution} вместо переменной: "
        ),
    )


def _difference_over_factor_plan(
    formula: str, match: re.Match[str], context: dict[str, Any]
) -> RepairPlan:
    coefficient_raw = match["coefficient"]
    coefficient_text = coefficient_raw or "1"
    coefficient = int(coefficient_text)
    linear = f"{coefficient_raw}x" if coefficient_raw else "x"
    coefficient_square_text = match["coefficient_square"] or "1"
    coefficient_square = int(coefficient_square_text)
    term, term_square = int(match["term"]), int(match["term_square"])
    sign = match["sign"]
    if coefficient_square != coefficient**2 or term_square != term**2:
        raise RightTrianglePlanError("numerator must be a difference of squares")
    remaining_sign = "-" if sign == "+" else "+"
    answer = -term if sign == "+" else term
    factor_left = f"{linear}-{term}"
    factor_right = f"{linear}+{term}"
    denominator = f"{linear}{sign}{term}"
    primary = (
        f"{formula}=\\frac{{({factor_left})({factor_right})}}{{{denominator}}}"
        f"-{linear}={linear}{remaining_sign}{term}-{linear}={answer}"
    )
    numerator_at_one = coefficient_square - term_square
    denominator_at_one = coefficient + (term if sign == "+" else -term)
    if denominator_at_one == 0:
        raise RightTrianglePlanError("x=1 is outside the expression domain")
    alternative = (
        f"\\frac{{{coefficient_square}\\cdot 1^2-{term_square}}}"
        f"{{{coefficient}\\cdot 1{sign}{term}}}-{coefficient}\\cdot 1="
        f"\\frac{{{numerator_at_one}}}{{{denominator_at_one}}}-{coefficient}="
        f"{numerator_at_one // denominator_at_one}-{coefficient}={answer}"
    )
    return _plan(context, answer=answer, primary=primary, alternative=alternative, variable="x")


def _conjugate_product_minus_square_plan(
    formula: str, match: re.Match[str], context: dict[str, Any]
) -> RepairPlan:
    """Use the difference of squares, then verify by substituting x=1."""

    coefficient = int(match["coefficient"] or "1")
    coefficient_text = match["coefficient"] or "1"
    term = int(match["term"])
    square = int(match["square"] or "1")
    if square != coefficient**2 or match["first_sign"] == match["second_sign"]:
        raise RightTrianglePlanError("subtracted square must match the conjugate coefficient")
    answer = -term**2
    linear = f"{coefficient_text}x"
    primary = (
        f"{formula}=({linear})^{{2}}-{term**2}-{square}x^{{2}}="
        f"{square}x^{{2}}-{term**2}-{square}x^{{2}}={answer}"
    )
    alternative = (
        f"({coefficient_text}\\cdot1{match['first_sign']}{term})"
        f"({coefficient_text}\\cdot1{match['second_sign']}{term})-{square}\\cdot1^{{2}}="
        f"({coefficient}{match['first_sign']}{term})({coefficient}{match['second_sign']}{term})-{square}="
        f"{coefficient + (term if match['first_sign'] == '+' else -term)}\\cdot"
        f"{coefficient + (term if match['second_sign'] == '+' else -term)}-{square}={answer}"
    )
    html = (
        '<p>Используем формулу разности квадратов:</p>'
        '<center><p><span data-inline-latex="(a-b)(a+b)=a^{2}-b^{2}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменная <span data-inline-latex="x"></span> '
        'в ответе быть не может, значит, она должна сократиться.</p>'
        '<p>Подставим <span data-inline-latex="x=1"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
    )
    content = _normalized_content(context)
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != str(answer):
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=str(answer), transformations=tuple(changes))


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Preserve factorization, then provide a short first-part substitution method."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("algebraic expression conditions must be text-only")
    formula = _formula(condition)
    if match := _COMMON_FACTOR.fullmatch(formula):
        return _common_factor_plan(formula, match, context)
    if match := _RECIPROCAL_DIFFERENCE.fullmatch(formula):
        return _reciprocal_difference_plan(formula, match, context)
    if match := _DIFFERENCE_OVER_FACTOR.fullmatch(formula):
        return _difference_over_factor_plan(formula, match, context)
    if match := _CONJUGATE_PRODUCT_MINUS_SQUARE.fullmatch(formula):
        return _conjugate_product_minus_square_plan(formula, match, context)
    raise RightTrianglePlanError("condition does not match a registered algebraic cancellation form")
