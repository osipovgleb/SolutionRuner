"""Plans for ratios ``P(b) / P(1/b)`` with reciprocal factors."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_DEFINITION = re.compile(
    r"^p\(b\)=\(b(?P<first>[+-])\\frac\{(?P<coefficient>\d+)\}\{b\}\)"
    r"\((?P<negative>-?)(?P<second_coefficient>\d*)b(?P<second>[+-])\\frac\{1\}\{b\}\)$"
)


def _fraction_latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    return f"{sign}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _factor_latex(value: Fraction) -> str:
    rendered = _fraction_latex(value)
    return f"({rendered})" if value < 0 else rendered


def _formulae(condition: dict[str, Any]) -> list[str]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    return [
        str(node.get("data-inline-latex") or "").replace(" ", "")
        for node in soup.find_all("span", attrs={"data-inline-latex": True})
    ]


def _solution_html(primary_steps: list[str], ratio: str, alternative: str) -> str:
    centered = lambda formula: f'<center><p><span data-inline-latex="{formula}"></span>.</p></center>'
    return (
        '<p>Вычислим значения функции:</p>'
        + "".join(centered(step) for step in primary_steps)
        + '<p>Подставим полученные значения:</p>'
        + centered(ratio)
        + '<p><b>Приведем другое решение</b></p>'
        + '<p>Так как это задание первой части, переменной '
        '<span data-inline-latex="b"></span> в ответе быть не может, значит, '
        'она должна сократиться. Подставим, например, 5 вместо переменной:</p>'
        + centered(alternative)
    )


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("polynomial ratio condition must be text-only")
    definition = next((item for item in _formulae(condition) if item.startswith("p(b)=")), None)
    match = _DEFINITION.fullmatch(definition or "")
    if not match:
        raise RightTrianglePlanError("condition does not match a reciprocal polynomial ratio")

    coefficient = int(match["coefficient"])
    first, second = match["first"], match["second"]
    second_coefficient = match["second_coefficient"] or "1"
    is_plus = first == "+" and not match["negative"] and second == "+"
    is_minus = first == "-" and match["negative"] == "-" and second == "+"
    if not (is_plus or is_minus) or int(second_coefficient) != coefficient:
        raise RightTrianglePlanError("factors are not reciprocal counterparts")

    substitution = 1 if (is_plus or coefficient != 1) else 2
    if is_plus:
        p_b = f"p(b)=(b+\\frac{{{coefficient}}}{{b}})({coefficient}b+\\frac{{1}}{{b}})"
        p_inverse_simplified = f"(\\frac{{1}}{{b}}+{coefficient}b)(\\frac{{{coefficient}}}{{b}}+b)"
        p_inverse = (
            f"p(\\frac{{1}}{{b}})=(\\frac{{1}}{{b}}+\\frac{{{coefficient}}}{{\\frac{{1}}{{b}}}})"
            f"(\\frac{{{coefficient}}}{{b}}+\\frac{{1}}{{\\frac{{1}}{{b}}}})="
            f"{p_inverse_simplified}"
        )
        first = Fraction(substitution) + Fraction(coefficient, substitution)
        second = Fraction(coefficient * substitution) + Fraction(1, substitution)
        expression_at_value = (
            f"\\frac{{({substitution}+\\frac{{{coefficient}}}{{{substitution}}})"
            f"({substitution}\\cdot {coefficient}+\\frac{{1}}{{{substitution}}})}}"
            f"{{(\\frac{{1}}{{{substitution}}}+{substitution}\\cdot {coefficient})"
            f"(\\frac{{{coefficient}}}{{{substitution}}}+{substitution})}}="
            f"\\frac{{{_factor_latex(first)}\\cdot {_factor_latex(second)}}}"
            f"{{{_factor_latex(second)}\\cdot {_factor_latex(first)}}}=1"
        )
    else:
        p_b = f"p(b)=(b-\\frac{{{coefficient}}}{{b}})(-{coefficient}b+\\frac{{1}}{{b}})"
        p_inverse_simplified = f"(\\frac{{1}}{{b}}-{coefficient}b)(-\\frac{{{coefficient}}}{{b}}+b)"
        p_inverse = (
            f"p(\\frac{{1}}{{b}})=(\\frac{{1}}{{b}}-\\frac{{{coefficient}}}{{\\frac{{1}}{{b}}}})"
            f"(-\\frac{{{coefficient}}}{{b}}+\\frac{{1}}{{\\frac{{1}}{{b}}}})="
            f"{p_inverse_simplified}"
        )
        first = Fraction(substitution) - Fraction(coefficient, substitution)
        second = -Fraction(coefficient * substitution) + Fraction(1, substitution)
        expression_at_value = (
            f"\\frac{{({substitution}-\\frac{{{coefficient}}}{{{substitution}}})"
            f"(-{coefficient}\\cdot {substitution}+\\frac{{1}}{{{substitution}}})}}"
            f"{{(\\frac{{1}}{{{substitution}}}-{coefficient}\\cdot {substitution})"
            f"(-\\frac{{{coefficient}}}{{{substitution}}}+{substitution})}}="
            f"\\frac{{{_factor_latex(first)}\\cdot {_factor_latex(second)}}}"
            f"{{{_factor_latex(second)}\\cdot {_factor_latex(first)}}}=1"
        )
    p_b_expression = p_b.split("=", 1)[1]
    ratio = (
        f"\\frac{{p(b)}}{{p(\\frac{{1}}{{b}})}}="
        f"\\frac{{{p_b_expression}}}{{{p_inverse_simplified}}}=1"
    )
    html = _solution_html([p_b, p_inverse], ratio, expression_at_value).replace(
        "Подставим, например, 5 вместо переменной:",
        f"Подставим, например, {substitution} вместо переменной:",
    )

    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != "1":
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", '<p><span data-effect="spaced">1</span></p>'
        ))
    return RepairPlan(answer="1", transformations=tuple(changes))
