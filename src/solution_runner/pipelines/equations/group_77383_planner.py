"""Fail-closed reciprocal linear-equation solver for group 77383."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from ..core.numbers import format_answer
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .equation_conditions import read_equation_prompt
from .linear_fraction import solve_reciprocal_linear_equation

RULE = "elementary-equations-77383-reciprocal-linear"
_F = re.compile(
    r"\\frac\{(?P<n>-?\d+)\}\{(?P<a>-?\d*)x(?P<s>[+-])(?P<b>\d+)\}=(?:\\frac\{(?P<m>-?\d+)\}\{(?P<c>-?\d+)\}|(?P<r>-?\d+))"
)


def _condition_formula(condition_html: str) -> tuple[str, re.Match[str]]:
    formula = read_equation_prompt(condition_html, error_type=RightTrianglePlanError)
    match = _F.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("unsupported reciprocal linear equation")
    return formula, match


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 77383 must not have assets")
    c = _normalized_content(context)
    q = _section(c, "condition")
    ans = _section(c, "answer")
    sol = _section(c, "solution")
    if q is None or c.get("assets") or tuple(q.get("asset_keys") or ()):
        raise RightTrianglePlanError("condition incomplete")
    f, m = _condition_formula(str(q.get("html") or ""))
    n = int(m["n"])
    a = -1 if m["a"] == "-" else int(m["a"] or "1")
    b = int(m["b"]) if m["s"] == "+" else -int(m["b"])
    if m["r"] is None:
        right = int(m["c"])
        numerator_right = int(m["m"])
        left_product = n * right
    else:
        right = 1
        numerator_right = int(m["r"])
        left_product = n
    if not n or not a or not right or not numerator_right:
        raise RightTrianglePlanError("zero denominator coefficient")
    try:
        root = solve_reciprocal_linear_equation(
            Fraction(n), Fraction(a), Fraction(b), Fraction(numerator_right, right)
        )
    except ValueError as exc:
        raise RightTrianglePlanError(str(exc)) from exc
    try:
        value = format_answer(root)
    except ValueError as exc:
        raise RightTrianglePlanError(str(exc)) from exc
    prefix = "" if a == 1 else "-" if a == -1 else str(a)
    left_linear = f"{prefix}x{m['s']}{abs(b)}"
    coefficient = numerator_right * a
    constant = numerator_right * b
    rhs = left_product - constant
    steps = (
        f,
        f"{left_product}={numerator_right}\\cdot({left_linear})",
        f"{left_product}={coefficient}x{('+' if constant >= 0 else '-')}{abs(constant)}",
        f"{coefficient}x={rhs}",
        f"x={value.replace(',', '{,}')}",
    )
    h = "<p>По­сле­до­ва­тель­но по­лу­ча­ем:</p>" + "".join(
        f'<center><p><span data-inline-latex="{step}"></span>.</p></center>'
        for step in steps
    )
    ch = []
    if sol is None or sol.get("html") != h:
        ch.append(_section_transformation(sol, "solution", "Решение", h))
    cur = (
        BeautifulSoup(str(ans.get("html") or "") if ans else "", "html.parser")
        .get_text("", strip=True)
        .replace(" ", "")
    )
    if cur != value:
        ch.append(
            _section_transformation(
                ans,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{value}</span></p>',
            )
        )
    return RepairPlan(answer=value, transformations=tuple(ch))
