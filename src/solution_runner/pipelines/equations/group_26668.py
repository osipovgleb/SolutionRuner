"""Fail-closed parent-template planner for group 26668.

The parent establishes the editorial scaffold: square both sides, keep the
condition ``x <= 0``, solve the resulting quadratic, then select the root
requested by the child. Each child still supplies its own coefficients and
its own smaller/larger-root instruction.
"""

from __future__ import annotations

from fractions import Fraction
from math import isqrt
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer, parse_rational
from solution_runner.pipelines.equations.group_26656 import RepairPlan


RULE = "irrational-26668-square-root-negative-x"

_FORMULA = re.compile(
    r"\\sqrt\{(?P<constant_sign>[+-]?)(?P<constant>[1-9]\d*)"
    r"(?P<linear_sign>[+-])(?P<coefficient>[1-9]\d*)?x\}=(?P<right_sign>[+-]?)x"
)
_CONDITION = re.compile(
    r"Найдите корень уравнения:? (?P<formula>.+?)\s*\. "
    r"Если уравнение имеет более одного корня, укажите (?P<choice>меньший|больший) из них\."
)


class UnsupportedCondition(ValueError):
    """Raised before any mutation for a condition outside the audited form."""


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [item for item in content.get("sections", []) if item.get("key") == key]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    target = str((section or {}).get("transformation_target_id") or "")
    if not target:
        target = f"section:{key}"
    return {
        "transformation_target_id": target,
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    visible = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True)
    try:
        return parse_rational(visible) == parse_rational(expected)
    except ValueError:
        return False


def _condition_parts(condition_html: str) -> tuple[str, int, int, int, str]:
    soup = BeautifulSoup(condition_html, "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text("", strip=True) or set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    spans[0].replace_with(formula)
    visible = " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split())
    match = _CONDITION.fullmatch(visible)
    if match is None or match.group("formula") != formula:
        raise UnsupportedCondition("condition does not match group 26668")
    formula_match = _FORMULA.fullmatch(formula)
    if formula_match is None:
        raise UnsupportedCondition("unsupported square-root negative-x equation")
    constant = int(formula_match.group("constant"))
    if formula_match.group("constant_sign") == "-":
        constant = -constant
    coefficient = int(formula_match.group("coefficient") or "1")
    if formula_match.group("linear_sign") == "-":
        coefficient = -coefficient
    right_sign = -1 if formula_match.group("right_sign") == "-" else 1
    return formula, constant, coefficient, right_sign, match.group("choice")


def _roots(
    constant: int, coefficient: int, right_sign: int
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    """Solve ``x² - coefficient*x - constant = 0`` and enforce RHS sign."""

    discriminant = coefficient * coefficient + 4 * constant
    if discriminant < 0:
        raise UnsupportedCondition("quadratic has no real roots")
    square_root = isqrt(discriminant)
    if square_root * square_root != discriminant:
        raise UnsupportedCondition("quadratic roots are irrational")
    numerators = (coefficient - square_root, coefficient + square_root)
    roots = tuple(sorted({Fraction(numerator, 2) for numerator in numerators}))
    admissible = tuple(root for root in roots if right_sign * root >= 0)
    if not admissible:
        raise UnsupportedCondition("no root satisfies the right-hand-side sign")
    return roots, admissible


def _signed_term(value: int, *, variable: bool = False) -> str:
    magnitude = abs(value)
    suffix = "x" if variable else ""
    body = f"{magnitude}{suffix}" if magnitude != 1 or not variable else suffix
    return f"+{body}" if value >= 0 else f"-{body}"


def _affine_latex(constant: int, coefficient: int) -> str:
    first = str(constant)
    return f"{first}{_signed_term(coefficient, variable=True)}"


def _quadratic_latex(constant: int, coefficient: int) -> str:
    return f"x^{{2}}{_signed_term(-coefficient, variable=True)}{_signed_term(-constant)}=0"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Adapt the audited parent structure to one child of group 26668."""

    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("group 26668 does not allow assets")
    condition, answer, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition without assets is required")

    formula, constant, coefficient, right_sign, choice = _condition_parts(str(condition.get("html") or ""))
    roots, admissible = _roots(constant, coefficient, right_sign)
    selected = min(admissible) if choice == "меньший" else max(admissible)
    rendered_answer = format_answer(selected, allow_latex_fraction=True)
    roots_latex = r"\\".join(
        f"x={format_answer(root, allow_latex_fraction=True)}" for root in roots
    )
    admissible_latex = r"\\".join(
        f"x={format_answer(root, allow_latex_fraction=True)}" for root in admissible
    )
    sign_condition = "x\\ge 0" if right_sign > 0 else "x\\le 0"
    rhs = "x" if right_sign > 0 else "-x"
    final_step = (
        f"\\iff x={format_answer(admissible[0], allow_latex_fraction=True)}"
        if len(admissible) == 1
        else f"\\iff \\left[\\begin{{aligned}}{admissible_latex}\\end{{aligned}}\\right."
    )
    conclusion = "" if len(admissible) == 1 else f"<p>{choice.capitalize()} корень равен {rendered_answer}.</p>"
    solution_html = (
        "<p>Возведём в квадрат:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff \\begin{{cases}}{_affine_latex(constant, coefficient)}=x^{{2}}\\\\{rhs}\\ge 0\\end{{cases}}'
        f'\\iff \\begin{{cases}}{_quadratic_latex(constant, coefficient)}\\\\{sign_condition}\\end{{cases}}'
        f'\\iff \\begin{{cases}}\\left[\\begin{{aligned}}{roots_latex}\\end{{aligned}}\\right.\\\\{sign_condition}\\end{{cases}}'
        f'{final_step}"></span>.</p></center>'
        f"{conclusion}"
    )
    changes: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != solution_html:
        changes.append(_rewrite(solution, "solution", "Решение", solution_html))
    if not _answer_matches(answer, rendered_answer):
        changes.append(_rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{rendered_answer}</span></p>'))
    return RepairPlan(answer=rendered_answer, condition_html=str(condition.get("html") or ""), solution_html=solution_html, transformations=tuple(changes))
