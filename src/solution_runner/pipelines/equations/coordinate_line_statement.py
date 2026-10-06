"""Fail-closed plans for a numbered true-statement task on a coordinate line."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RightTrianglePlanError


_FORMULA = re.compile(r"^(?:(a)|(-?\d+))([+-])(?:(a)|(-?\d+))([<>])0$")
_POINT = re.compile(r'<path\b(?=[^>]*\bfill=["\']#143B8F["\'])(?=[^>]*\bd=["\']M([-\d.]+),([-\d.]+))[^>]*>')
_TICK = re.compile(r'<line\b[^>]*\bx1=["\']([-\d.]+)["\'][^>]*\bx2=["\']\1["\'][^>]*>')


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    transformations: tuple[dict[str, Any], ...]


def _formula(item: Any) -> str:
    soup = BeautifulSoup(str(item), "html.parser")
    latex = soup.find("span", attrs={"data-inline-latex": True})
    raw = str(latex.get("data-inline-latex") if latex else soup.get_text("", strip=True))
    normalized = (raw.replace("−", "-").replace("–", "-").replace(r"\gt", ">")
        .replace(r"\lt", "<").replace("{", "").replace("}", "").replace(" ", ""))
    if not _FORMULA.fullmatch(normalized):
        raise RightTrianglePlanError("option is not a reviewed linear inequality")
    return normalized


def _options(condition: dict[str, Any]) -> tuple[str, ...]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    items = soup.find_all("li")
    if len(items) != 4:
        items = soup.find_all("nobr")
    values = tuple(_formula(item) for item in items)
    if len(values) != 4:
        raise RightTrianglePlanError("condition must have four reviewed options")
    return values


def _vertical_options(condition: dict[str, Any]) -> str | None:
    """Put only the legacy inline option row into the platform's vertical list."""

    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    items = soup.find_all("nobr")
    if len(items) != 4:
        return None
    rows = []
    for index, item in enumerate(items, start=1):
        content = re.sub(rf"^\s*{index}\)\s*", "", item.decode_contents())
        rows.append(f"<li>{content}</li>")
    replacement = BeautifulSoup(
        f'<ol data-layout="source-options">{"".join(rows)}</ol>', "html.parser"
    ).ol
    assert replacement is not None
    items[0].replace_with(replacement)
    for item in items[1:]:
        item.extract()
    return str(soup)


def _representative(svg: bytes) -> tuple[int, int, Fraction]:
    try:
        text = svg.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RightTrianglePlanError("condition SVG is not UTF-8") from exc
    ticks = sorted({float(value) for value in _TICK.findall(text)})
    if len(ticks) < 3:
        raise RightTrianglePlanError("coordinate line has too few ticks")
    spacing = ticks[1] - ticks[0]
    if spacing <= 0 or any(abs(ticks[index + 1] - value - spacing) > 1.2 for index, value in enumerate(ticks[:-1])):
        raise RightTrianglePlanError("coordinate line ticks are not uniform")
    points = [(float(x), float(y)) for x, y in _POINT.findall(text)]
    if not points:
        raise RightTrianglePlanError("coordinate line marker is unavailable")
    point, _ = min(points, key=lambda value: abs(value[1] - 22))
    left = int((point - ticks[0]) // spacing)
    if not 0 <= left < len(ticks) - 1 or abs(point - ticks[left]) < spacing * .1 or abs(point - ticks[left + 1]) < spacing * .1:
        raise RightTrianglePlanError("coordinate line marker must lie strictly between ticks")
    return left, left + 1, Fraction(2 * left + 1, 2)


def _is_true(formula: str, value: Fraction) -> bool:
    result, comparison = _result(formula, value)
    return result > 0 if comparison == ">" else result < 0


def _result(formula: str, value: Fraction) -> tuple[Fraction, str]:
    match = _FORMULA.fullmatch(formula)
    assert match is not None
    left_a, left_number, operation, right_a, right_number, comparison = match.groups()
    left = value if left_a else Fraction(int(left_number))
    right = value if right_a else Fraction(int(right_number))
    return left + right if operation == "+" else left - right, comparison


def _latex(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator // value.denominator}{{,}}5"


def _solution(options: tuple[str, ...], lower: int, upper: int, value: Fraction) -> str:
    rows = []
    for index, formula in enumerate(options, start=1):
        substituted = formula.replace("a", _latex(value))[:-2]
        result, comparison = _result(formula, value)
        rows.append(
            f'<li><span data-inline-latex="{substituted}={_latex(result)}{comparison}0"></span> — '
            f'{"верно" if _is_true(formula, value) else "неверно"}.</li>'
        )
    return (
        f'<p>Из рисунка видно, что <span data-inline-latex="{lower}\\lt a\\lt {upper}"></span>. '
        f'Возьмём число <span data-inline-latex="a={_latex(value)}"></span> из этого промежутка и проверим утверждения.</p>'
        f'<ol data-layout="source-options">{"".join(rows)}</ol>'
    )


def build_context_repair_plan(
    context: dict[str, Any], *, condition_asset_bytes: bytes | None,
) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None:
        raise RightTrianglePlanError("condition is required")
    vertical = _vertical_options(condition)
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True)
    if solution_section is not None and current_answer in {"1", "2", "3", "4"}:
        changes = (() if vertical is None else (_section_transformation(
            condition, "condition", "Условие", vertical
        ),))
        return RepairPlan(answer=current_answer, transformations=changes)
    if condition_asset_bytes is None:
        raise RightTrianglePlanError("condition and its SVG are required")
    options = _options(condition)
    lower, upper, value = _representative(condition_asset_bytes)
    true_options = [index for index, formula in enumerate(options, start=1) if _is_true(formula, value)]
    if len(true_options) != 1:
        raise RightTrianglePlanError("coordinate line does not select one true option")
    answer = str(true_options[0])
    changes: list[dict[str, Any]] = []
    if vertical is not None:
        changes.append(_section_transformation(
            condition, "condition", "Условие", vertical
        ))
    if solution_section is None:
        changes.append(_section_transformation(
            None, "solution", "Решение", _solution(options, lower, upper, value)
        ))
    if current_answer != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))
