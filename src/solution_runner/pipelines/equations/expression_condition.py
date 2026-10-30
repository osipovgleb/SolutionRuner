"""Validate the whole question before legacy formula-specific arithmetic."""

import re

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section
from ..triangles.right.planner import RightTrianglePlanError

_FORMULA = "\ufff0"
_VALUE = r"[a-z]\s*=\s*[−–-]?\d+(?:[,.]\d+)?"
_QUESTION = re.compile(
    rf"(?:Найдите(?: значение выражения)?|Вычислите):? {_FORMULA}"
    rf"(?:, если {_FORMULA}(?:(?:, (?:а )?| при |, при |\. При ){_FORMULA})?"
    rf"| при (?:{_FORMULA}|{_VALUE}))?\.?"
)
_FORMULAS_ONLY = re.compile(
    rf"{_FORMULA}(?: {_FORMULA}){{0,2}}(?: при (?:{_FORMULA}|{_VALUE}))?\.?"
)
_PLAIN_NUMERIC = re.compile(
    r"(?:Найдите значение выражения|Вычислите):? [\d\s,.()+*/^·×÷:−–-]+"
)


def normalized_content(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("a complete expression condition is required")
    html = str(condition.get("html") or "")
    if _FORMULA in html:
        raise RightTrianglePlanError("reserved formula marker in condition")
    soup = BeautifulSoup(html, "html.parser")
    if _FORMULA in soup.get_text():
        raise RightTrianglePlanError("reserved formula marker in condition")
    for tag in list(soup.find_all(True)):
        if tag.name == "span" and set(tag.attrs) == {"data-inline-latex"}:
            if not tag["data-inline-latex"] or tag.get_text().strip():
                raise RightTrianglePlanError("ambiguous visible mathematical formula")
            tag.replace_with(" " + _FORMULA + " ")
        elif tag.name == "var":
            if (
                set(tag.attrs) != {"data-math-identifier"}
                or tag.get_text() != tag["data-math-identifier"]
                or not re.fullmatch("[a-z]", tag.get_text())
            ):
                raise RightTrianglePlanError("unsupported expression variable markup")
            tag.unwrap()
        elif (
            tag.name not in {"p", "br", "nobr", "center", "i", "em", "b", "strong"}
            or tag.attrs
        ):
            raise RightTrianglePlanError("unsupported expression condition markup")
    text = " ".join(
        soup.get_text(" ", strip=True)
        .replace("\xad", "")
        .replace("\u202f", " ")
        .split()
    )
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    if (
        _QUESTION.fullmatch(text) is None
        and _FORMULAS_ONLY.fullmatch(text) is None
        and _PLAIN_NUMERIC.fullmatch(text) is None
    ):
        raise RightTrianglePlanError(
            "unsupported complete expression question or additional instruction"
        )
    return content
