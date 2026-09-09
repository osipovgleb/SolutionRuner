"""Small fail-closed primitives shared by verbal-arithmetic rules."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, parse_rational


class UnsupportedCondition(ValueError):
    """The source condition is outside an audited deterministic template."""


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    condition_html: str
    solution_html: str
    transformations: tuple[dict[str, Any], ...] = ()


def section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [item for item in content.get("sections", []) if isinstance(item, dict) and item.get("key") == key]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def visible_plain_paragraph(html: str, *, allow_inline_latex: bool = False) -> str:
    """Return normalized condition text from audited paragraph markup."""

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")

    def has_meaningful_markup(paragraph: Any) -> bool:
        if paragraph.attrs:
            return True
        for tag in paragraph.find_all(True):
            if allow_inline_latex and tag.name == "span" and set(tag.attrs) == {"data-inline-latex"}:
                formula = str(tag["data-inline-latex"]).replace(r"\%", "%")
                tag.replace_with(formula)
            elif allow_inline_latex and tag.name == "nobr" and not tag.attrs:
                continue
            elif tag.attrs or tag.get_text("", strip=True):
                return True
        return False

    if not paragraphs or any(has_meaningful_markup(paragraph) for paragraph in paragraphs):
        raise UnsupportedCondition("condition must contain only plain paragraphs")
    if any(
        node.name != "p"
        and not (allow_inline_latex and node.name == "nobr" and not node.attrs)
        and (node.attrs or node.get_text("", strip=True))
        for node in soup.find_all(True)
    ):
        raise UnsupportedCondition("condition markup is unsupported")
    text = " ".join(
        " ".join(paragraph.get_text(" ", strip=True) for paragraph in paragraphs).replace("\u00ad", "").replace("\u202f", " ").split()
    )
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def require_content(
    context: dict[str, Any], *, allow_inline_latex: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None, str]:
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("this verbal rule does not allow assets")
    condition, answer, solution = (section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition without assets is required")
    html = str(condition.get("html") or "")
    return content, condition, answer, solution, visible_plain_paragraph(
        html, allow_inline_latex=allow_inline_latex,
    )


def rewrite(item: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    target = str((item or {}).get("transformation_target_id") or f"section:{key}")
    return {
        "transformation_target_id": target,
        "operation": "rewrite" if item is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def answer_matches(item: dict[str, Any] | None, expected: str) -> bool:
    if item is None:
        return False
    text = BeautifulSoup(str(item.get("html") or ""), "html.parser").get_text("", strip=True)
    try:
        return parse_rational(text) == parse_rational(expected)
    except (NumberFormatError, ValueError):
        return False


def decimal_latex(value: Fraction | int) -> str:
    return format_answer(Fraction(value)).replace(",", "{,}")


def mixed_latex(value: Fraction) -> str:
    whole, remainder = divmod(value.numerator, value.denominator)
    if remainder == 0:
        return str(whole)
    return rf"{whole}\frac{{{remainder}}}{{{value.denominator}}}"


def finalize(
    condition: dict[str, Any],
    answer_section: dict[str, Any] | None,
    solution_section: dict[str, Any] | None,
    answer: int,
    solution_html: str,
    *,
    legacy_solution_html: str | None = None,
    rewrite_existing_solution: bool = False,
) -> RepairPlan:
    rendered = str(answer)
    transformations: list[dict[str, Any]] = []
    # Source-authored solutions are authoritative.  A word-problem runner may
    # supply a solution only when the task has none; it must never replace an
    # existing editorial solution just because its own wording differs.
    current_solution = str((solution_section or {}).get("html") or "")
    if rewrite_existing_solution or solution_section is None or legacy_solution_html == current_solution:
        transformations.append(rewrite(solution_section, "solution", "Решение", solution_html))
    if not answer_matches(answer_section, rendered):
        transformations.append(rewrite(answer_section, "answer", "Ответ", f"<p>{rendered}</p>"))
    return RepairPlan(rendered, str(condition.get("html") or ""), solution_html, tuple(transformations))
