"""Linear fraction equations with equal constant numerators or equal denominators."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer, format_latex_fraction

from .equation_conditions import read_equation_prompt
from .exponential_affine import _parse_linear
from .group_26656 import RepairPlan, _rewrite, _section

RULE = "elementary-equations-315119-equal-unit-fractions"
_FRACTIONS = re.compile(
    r"\\frac\{(?P<ln>[^{}]+)\}\{(?P<ld>[^{}]+)\}="
    r"\\frac\{(?P<rn>[^{}]+)\}\{(?P<rd>[^{}]+)\}"
)


class UnsupportedCondition(ValueError):
    """Reject unsupported fraction forms before planning any changes."""


def _affine(value: str) -> tuple[int, int]:
    return (int(value), 0) if re.fullmatch(r"[+-]?\d+", value) else _parse_linear(value)


def _solve(formula: str) -> RepairPlan:
    match = _FRACTIONS.fullmatch(formula)
    if match is None:
        raise UnsupportedCondition("two affine fractions are required")
    ln, ld, rn, rd = (_affine(match[key]) for key in ("ln", "ld", "rn", "rd"))
    if ld == rd:
        left, right = match["ln"], match["rn"]
        left_values, right_values = ln, rn
        introduction = (
            "Если две дроби с равным знаменателем равны, то равны их числители. Имеем:"
        )
    elif ln == rn and ln[1] == 0 and ln[0] != 0:
        left, right = match["ld"], match["rd"]
        left_values, right_values = ld, rd
        introduction = "Если две дроби с равными ненулевыми числителями равны, то равны их знаменатели. Имеем:"
    else:
        raise UnsupportedCondition(
            "fractions need an equal denominator or an equal nonzero constant numerator"
        )
    constant = right_values[0] - left_values[0]
    coefficient = left_values[1] - right_values[1]
    if not coefficient:
        raise UnsupportedCondition("fraction equation does not have a unique root")
    root = Fraction(constant, coefficient)
    if not (ld[0] + ld[1] * root) or not (rd[0] + rd[1] * root):
        raise UnsupportedCondition("root violates the denominator domain")
    domain = r"\\".join(dict.fromkeys((f"{match['ld']}\\ne 0", f"{match['rd']}\\ne 0")))
    excluded = [
        f"x\\ne {format_latex_fraction(Fraction(-c, k))}"
        for c, k in dict.fromkeys((ld, rd))
        if k
    ]
    exact = format_latex_fraction(root)
    prefix = "" if coefficient == 1 else "-" if coefficient == -1 else str(coefficient)
    steps = [
        formula,
        f"\\begin{{cases}}{left}={right}\\\\{domain}\\end{{cases}}",
        f"\\begin{{cases}}{prefix}x={constant}\\\\{domain}\\end{{cases}}",
    ]
    if excluded:
        steps.append(
            f"\\begin{{cases}}x={exact}\\\\" + r"\\".join(excluded) + r"\end{cases}"
        )
    steps.append(f"x={exact}")
    html = f"<p>{introduction}</p>" + "".join(
        f'<center><p><span data-inline-latex="{step}"></span>.</p></center>'
        for step in steps
    )
    return RepairPlan(
        answer=format_answer(root, allow_latex_fraction=True),
        condition_html="",
        solution_html=html,
    )


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    content = context.get("normalized_content")
    if (
        parent_condition_asset_id
        or not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets")
    ):
        raise UnsupportedCondition("schema-v3 assetless content is required")
    condition, answer, solution = (
        _section(content, key) for key in ("condition", "answer", "solution")
    )
    if condition is None or condition.get("asset_keys"):
        raise UnsupportedCondition("canonical condition is required")
    planned = _solve(read_equation_prompt(str(condition.get("html") or "")))
    changes = []
    if solution is None or solution.get("html") != planned.solution_html:
        changes.append(_rewrite(solution, "solution", "Решение", planned.solution_html))
    current = BeautifulSoup(
        str(answer.get("html") or "") if answer else "", "html.parser"
    ).get_text("", strip=True)
    if current != planned.answer:
        changes.append(
            _rewrite(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{planned.answer}</span></p>',
            )
        )
    return RepairPlan(
        answer=planned.answer,
        condition_html=str(condition.get("html") or ""),
        solution_html=planned.solution_html,
        transformations=tuple(changes),
    )
