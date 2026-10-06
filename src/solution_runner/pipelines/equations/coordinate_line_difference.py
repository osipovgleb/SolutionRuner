"""Choose a signed difference from the left-to-right order on a coordinate line."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RightTrianglePlanError


_POINT = re.compile(r'<path\b(?=[^>]*\bfill=["\']#143B8F["\'])(?=[^>]*\bd=["\']M([-\d.]+),([-\d.]+))[^>]*>', re.I)
_UNCOLORED_POINT = re.compile(r'<path\b[^>]*\bd=["\']M([-\d.]+),([-\d.]+)c-1\.17[^>]*>', re.I)
_CIRCLE = re.compile(r'<circle\b(?=[^>]*\bfill=["\']#143B8F["\'])[^>]*\bcx=["\']([-\d.]+)["\']', re.I)
_LETTER_MAP = str.maketrans({"а": "a", "с": "c", "х": "x", "у": "y", "р": "p"})


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    transformations: tuple[dict[str, Any], ...]


def _plain(value: str) -> str:
    return value.replace("\u00ad", "").replace("−", "-").replace("–", "-")


def _letters(item: Any) -> list[str]:
    return [letter for tag in item.find_all("i") for letter in re.findall(r"[abcxyzpqr]", tag.get_text("", strip=True).translate(_LETTER_MAP))]


def _names(condition: dict[str, Any]) -> list[str]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    names = list(dict.fromkeys(_letters(soup)[:3]))
    if len(names) != 3:
        raise RightTrianglePlanError("coordinate variables are unavailable")
    return names


def _options(condition: dict[str, Any]) -> list[tuple[str, str] | None]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    items = soup.find_all("li")
    if len(items) != 4:
        numbered: list[tuple[int, Any]] = []
        for tag in soup.find_all(["nobr", "p"]):
            match = re.match(r"\s*([1-4])\)", _plain(tag.get_text("", strip=True)))
            if match:
                numbered.append((int(match.group(1)), tag))
        items = [tag for _, tag in sorted(numbered)]
    if len(items) != 4:
        raise RightTrianglePlanError("condition must contain four options")
    result: list[tuple[str, str] | None] = []
    for item in items:
        letters = _letters(item)
        result.append((letters[0], letters[1]) if len(letters) == 2 else None)
    return result


def _points(svg: bytes) -> list[float]:
    try:
        text = svg.decode("utf-8")
        points = sorted({float(value[0]) for value in _POINT.findall(text)})
        if len(points) != 3:
            points = sorted({float(value) for value in _CIRCLE.findall(text)})
        if len(points) != 3:
            points = sorted({float(value[0]) for value in _UNCOLORED_POINT.findall(text)})
    except UnicodeDecodeError as exc:
        raise RightTrianglePlanError("condition SVG is not UTF-8") from exc
    if len(points) != 3:
        raise RightTrianglePlanError("coordinate line markers are not reviewed")
    return points


def _selected(options: list[tuple[str, str] | None], positions: dict[str, float], positive: bool) -> list[int]:
    matches = [index for index, pair in enumerate(options[:3], 1) if pair and ((positions[pair[0]] > positions[pair[1]]) == positive)]
    return matches or ([4] if options[3] is None else [])


def _positions(names: list[str], points: list[float], options: list[tuple[str, str] | None], positive: bool, source_answer: str) -> dict[str, float]:
    if source_answer not in {"1", "2", "3", "4"}:
        raise RightTrianglePlanError("source answer is not a reviewed option")
    candidates = []
    for order in permutations(names):
        positions = dict(zip(order, points))
        if _selected(options, positions, positive) == [int(source_answer)]:
            candidates.append(positions)
    if len(candidates) != 1:
        raise RightTrianglePlanError("coordinate labels are ambiguous")
    return candidates[0]


def build_context_repair_plan(
    context: dict[str, Any], *, condition_asset_bytes: bytes | None,
) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or condition_asset_bytes is None:
        raise RightTrianglePlanError("condition SVG is required")
    names = _names(condition)
    options = _options(condition)
    prompt = _plain(BeautifulSoup(str(condition.get("html") or ""), "html.parser").get_text(" ", strip=True)).lower()
    positive = "положительна" in prompt or "положительно" in prompt
    negative = "отрицательна" in prompt or "отрицательно" in prompt
    if positive == negative:
        raise RightTrianglePlanError("question must request one sign")
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True)
    positions = _positions(names, _points(condition_asset_bytes), options, positive, current_answer)
    matches = _selected(options, positions, positive)
    if len(matches) != 1:
        raise RightTrianglePlanError("coordinate line does not select one option")
    answer = str(matches[0])
    ordered = "<".join(sorted(names, key=positions.__getitem__))
    rows = []
    for index, pair in enumerate(options[:3], 1):
        assert pair is not None
        sign = ">" if positions[pair[0]] > positions[pair[1]] else "<"
        rows.append(f'<li><span data-inline-latex="{pair[0]}-{pair[1]}{sign}0"></span>.</li>')
    requested = "положительна" if positive else "отрицательна"
    html = (
        f'<p>По рисунку: <span data-inline-latex="{ordered}"></span>. Проверим разности.</p>'
        f'<ol data-layout="source-options">{"".join(rows)}</ol>'
        f'<p>Значит, разность {answer} {requested}.</p>'
    )
    changes = [_section_transformation(solution, "solution", "Решение", html)]
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer, tuple(changes))
