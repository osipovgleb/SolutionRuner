"""Plans for a linear ratio whose value follows from a:b."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_TARGET = re.compile(
    r"^\\frac\{a(?P<n_b>[+-]\d*)b(?P<n_c>[+-]\d+)\}\{a(?P<d_b>[+-]\d*)b(?P<d_c>[+-]\d+)\}$"
)
_RATIO = re.compile(r"^\\frac\{a\}\{b\}=(?P<value>-?\d+)$")


def _number(value: str) -> int:
    if value == "+":
        return 1
    if value == "-":
        return -1
    return int(value.replace("+", ""))


def _formulae(condition: dict[str, Any]) -> tuple[str, str]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    values = [str(item.get("data-inline-latex") or "").replace(" ", "") for item in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(values) != 2:
        raise RightTrianglePlanError("condition must contain the target ratio and a:b ratio")
    return values[0], values[1]


def _fraction_latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Replace a with kb and cancel the resulting common linear factor."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("proportional linear ratio condition must be text-only")
    target, ratio = _formulae(condition)
    target_match, ratio_match = _TARGET.fullmatch(target), _RATIO.fullmatch(ratio)
    if target_match is None or ratio_match is None:
        raise RightTrianglePlanError("condition does not match a registered proportional linear ratio")
    k = int(ratio_match["value"])
    n_b, n_c = _number(target_match["n_b"]), _number(target_match["n_c"])
    d_b, d_c = _number(target_match["d_b"]), _number(target_match["d_c"])
    numerator_b, denominator_b = k + n_b, k + d_b
    if denominator_b == 0:
        raise RightTrianglePlanError("substitution gives a zero b coefficient in the denominator")
    answer_value = Fraction(numerator_b, denominator_b)
    answer = _fraction_latex(answer_value)
    if n_c * denominator_b != d_c * numerator_b:
        raise RightTrianglePlanError("numerator and denominator do not have a common linear factor")
    numerator = f"{numerator_b}b{target_match['n_c']}"
    denominator = f"{denominator_b}b{target_match['d_c']}"
    factor = f"{denominator_b}b{target_match['d_c']}"
    primary = f"{ratio}\\iff a={k}b"
    calculation = f"{target}=\\frac{{{k}b{target_match['n_b']}b{target_match['n_c']}}}{{{k}b{target_match['d_b']}b{target_match['d_c']}}}=\\frac{{{numerator}}}{{{denominator}}}=\\frac{{{answer}({factor})}}{{{factor}}}={answer}"
    html = (
        '<p>Из условия получаем:</p>'
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p>Подставим это выражение в дробь:</p>'
        f'<center><p><span data-inline-latex="{calculation}"></span>.</p></center>'
    )
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))
