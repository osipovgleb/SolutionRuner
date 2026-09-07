"""Fail-closed planner for equations ``1 / sqrt(x) = 1 / n``."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import parse_rational


RULE = "irrational-511751-reciprocal-square-root"
_FORMULA = re.compile(
    r"\\frac\{1\}\{\\sqrt\{x\}\}=\\frac\{1\}\{(?P<root>[1-9]\d*)\}"
)


class UnsupportedCondition(ValueError):
    """Raised before mutation when a task is outside the frozen grammar."""


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    solution_html: str
    transformations: tuple[dict[str, Any], ...] = ()


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    sections = [
        section for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(sections) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return sections[0] if sections else None


def _target(section: dict[str, Any] | None, key: str) -> str:
    if section is not None:
        return str(section.get("transformation_target_id") or f"section:{section.get('section_id')}")
    return f"section:{key}"


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _answer_matches(section: dict[str, Any] | None, answer: str) -> bool:
    if section is None:
        return False
    current = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True)
    try:
        return parse_rational(current) == parse_rational(answer)
    except ValueError:
        return False


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build a minimal repair plan in the parent task's concise solution style."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets") not in (None, [])
    ):
        raise UnsupportedCondition("schema-v3 content without assets is required")
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")

    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation markup is unsupported")
    formula = str(spans[0].get("data-inline-latex") or "")
    match = _FORMULA.fullmatch(formula)
    if match is None:
        raise UnsupportedCondition("condition does not match reciprocal square-root grammar")

    root = int(match.group("root"))
    answer_text = str(root * root)
    solution_html = (
        "<p>Най­дем ко­рень урав­не­ния:</p><center><p> "
        f'<span data-inline-latex="{formula}\\iff \\sqrt{{x}}={root}\\iff x={answer_text}"></span>.  '
        "</p></center>"
    )
    transformations: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != solution_html:
        transformations.append(_rewrite(solution, "solution", "Решение", solution_html))
    if not _answer_matches(answer, answer_text):
        transformations.append(
            _rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{answer_text}</span></p>')
        )
    return RepairPlan(answer_text, solution_html, tuple(transformations))
