"""Plans for a requested linear expression derived from a fractional equality."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_FRACTIONAL_EQUALITY = re.compile(
    r"^\\frac\{(?P<numerator>[^{}]+)\}\{(?P<denominator>[^{}]+)\}=(?P<ratio>-?\d+)$"
)
_LINEAR = re.compile(
    r"^(?P<a>\d*)a(?P<b_sign>[+-])(?P<b>\d*)b(?P<constant_sign>[+-])(?P<constant>\d+)$"
)


def _coefficient(value: str) -> int:
    return int(value or "1")


def _linear(expression: str) -> tuple[int, int, int]:
    match = _LINEAR.fullmatch(expression)
    if match is None:
        raise RightTrianglePlanError("expression must be linear in a and b with a constant")
    a = _coefficient(match["a"])
    b = _coefficient(match["b"])
    constant = int(match["constant"])
    return (
        a,
        b if match["b_sign"] == "+" else -b,
        constant if match["constant_sign"] == "+" else -constant,
    )


def _term(value: int, variable: str = "") -> str:
    magnitude = abs(value)
    text = f"{magnitude}{variable}" if magnitude != 1 or not variable else variable
    return text if value >= 0 else f"-{text}"


def _linear_latex(a: int, b: int, constant: int) -> str:
    linear_part = f"{_term(a, 'a')}{'+' if b >= 0 else '-'}{_term(abs(b), 'b')}"
    if constant == 0:
        return linear_part
    return f"{linear_part}{'+' if constant > 0 else '-'}{abs(constant)}"


def _added_latex(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _normalizing_factor(derived: tuple[int, int, int], target: tuple[int, int, int]) -> int:
    """Return the integer factor that turns the derived linear part into target's."""

    candidates = [
        derived_coefficient // target_coefficient
        for derived_coefficient, target_coefficient in zip(derived[:2], target[:2])
        if target_coefficient != 0 and derived_coefficient % target_coefficient == 0
    ]
    if not candidates or len(set(candidates)) != 1 or candidates[0] == 0:
        raise RightTrianglePlanError("requested expression does not match the derived linear part")
    factor = candidates[0]
    if any(
        derived_coefficient != factor * target_coefficient
        for derived_coefficient, target_coefficient in zip(derived[:2], target[:2])
    ) or derived[2] % factor != 0:
        raise RightTrianglePlanError("derived expression cannot be normalized to the requested linear part")
    return factor


def _formulas(condition: dict[str, Any]) -> tuple[str, str]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [str(node.get("data-inline-latex") or "").replace(" ", "") for node in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(formulas) != 2:
        raise RightTrianglePlanError("condition must contain the requested expression and one equality")
    target, equality = formulas
    if not _FRACTIONAL_EQUALITY.fullmatch(equality):
        target, equality = equality, target
    if not _FRACTIONAL_EQUALITY.fullmatch(equality):
        raise RightTrianglePlanError("condition must contain a fractional equality")
    return target, equality


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Derive the matching linear expression, then shift its constant explicitly."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("shifted linear expression condition must be text-only")
    target, equality = _formulas(condition)
    target_a, target_b, target_constant = _linear(target)
    match = _FRACTIONAL_EQUALITY.fullmatch(equality)
    assert match is not None
    numerator_a, numerator_b, numerator_constant = _linear(match["numerator"])
    denominator_a, denominator_b, denominator_constant = _linear(match["denominator"])
    ratio = int(match["ratio"])

    derived = (
        ratio * denominator_a - numerator_a,
        ratio * denominator_b - numerator_b,
        ratio * denominator_constant - numerator_constant,
    )
    factor = _normalizing_factor(derived, (target_a, target_b, target_constant))
    normalized = tuple(value // factor for value in derived)
    shift = target_constant - normalized[2]
    raw_derived_latex = _linear_latex(*derived)
    derived_latex = _linear_latex(*normalized)
    numerator = match["numerator"]
    denominator = match["denominator"]
    multiplied_denominator = _linear_latex(
        ratio * denominator_a, ratio * denominator_b, ratio * denominator_constant
    )
    shift_latex = _added_latex(shift)
    primary = (
        f"{equality}\\iff {numerator}={ratio}({denominator})"
        f"\\iff {numerator}={multiplied_denominator}"
        f"\\iff {raw_derived_latex}=0"
        + (f"\\iff {derived_latex}=0" if factor != 1 else "")
    )
    result = f"{derived_latex}{shift_latex}=0{shift_latex}\\iff {target}={shift}"
    html = (
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p>Если сравнить выражение, которое требуется найти, и левую часть последнего равенства, '
        f'можно заметить, что они отличаются на <span data-inline-latex="{shift_latex}"></span>. '
        f'Поэтому прибавим к обеим частям равенства <span data-inline-latex="{shift_latex}"></span>:</p>'
        f'<center><p><span data-inline-latex="{result}"></span>.</p></center>'
    )
    answer = str(shift)
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))
