"""Shared exact counting, rounding and read-only content planning."""

from __future__ import annotations

import re
from fractions import Fraction

from bs4 import BeautifulSoup, NavigableString

from solution_runner.pipelines.core.numbers import format_answer, format_latex_fraction
from solution_runner.pipelines.word_problems.common import (
    RepairPlan,
    UnsupportedCondition,
    answer_matches,
    rewrite,
    section,
)
from solution_runner.pipelines.word_problems.common import (
    require_content as _require_content,
)

NUMBER = r"\d+(?:[,.]\d+|\{,\}\d+)?"
_WORDS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одного": 1,
    "одной": 1,
    "одно": 1,
    "раз": 1,
    "два": 2,
    "две": 2,
    "двух": 2,
    "три": 3,
    "трех": 3,
    "четыре": 4,
    "четырех": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
}
COUNT = (
    r"(?:\d+|"
    + "|".join(sorted(_WORDS, key=len, reverse=True))
    + r")(?: (?:один|одна|одно|два|две|три|четыре|пять|шесть|семь|восемь|девять))?"
)


def require_content(context, *, allow_inline_latex: bool = True):
    content = context.get("normalized_content")
    if not isinstance(content, dict):
        return _require_content(context, allow_inline_latex=allow_inline_latex)
    if not isinstance(content.get("sections"), list):
        raise UnsupportedCondition("normalized sections must be a list")
    condition = section(content, "condition")
    if condition is None:
        return _require_content(context, allow_inline_latex=allow_inline_latex)
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    for tag in soup.find_all(["b", "strong", "i", "em", "center"]):
        if tag.attrs:
            raise UnsupportedCondition(
                "only plain emphasis and centering wrappers are supported"
            )
        tag.unwrap()
    for node in list(soup.contents):
        if isinstance(node, NavigableString) and node.strip():
            paragraph = soup.new_tag("p")
            node.replace_with(paragraph)
            paragraph.append(node)
    readable = {**condition, "html": str(soup)}
    sections = [
        readable if item is condition else item for item in content.get("sections", [])
    ]
    prepared = {**context, "normalized_content": {**content, "sections": sections}}
    _, _, answer, solution, text = _require_content(
        prepared, allow_inline_latex=allow_inline_latex
    )
    return content, condition, answer, solution, text


def count(token: str) -> int:
    value = token.lower().replace("ё", "е")
    if value.isdigit():
        return int(value)
    parts = value.split()
    if len(parts) == 1 and value in _WORDS:
        return _WORDS[value]
    if (
        len(parts) == 2
        and _WORDS.get(parts[0], 0) >= 20
        and 0 < _WORDS.get(parts[1], 0) < 10
    ):
        return _WORDS[parts[0]] + _WORDS[parts[1]]
    raise UnsupportedCondition("unsupported count word")


def normalize(text: str) -> str:
    return (
        text.replace("ё", "е")
        .replace("\u2060", "")
        .replace("\u200b", "")
        .replace("‑", "-")
    )


def rounding(text: str) -> tuple[str, int | None]:
    match = re.search(
        r" (?:Результат|Ответ) округлите до (десятых|сотых|тысячных)\.$", text
    )
    if match is None:
        return text, None
    return text[: match.start()], {"десятых": 1, "сотых": 2, "тысячных": 3}[match[1]]


def rounded(value: Fraction, places: int) -> str:
    if value < 0 or places not in (1, 2, 3):
        raise UnsupportedCondition("unsupported probability rounding")
    scale = 10**places
    units = (2 * value.numerator * scale + value.denominator) // (2 * value.denominator)
    digits = str(units).zfill(places + 1)
    return digits[:-places] + "," + digits[-places:]


def line(formula: str) -> str:
    from html import escape

    return f'<center><p><span data-inline-latex="{escape(formula, quote=True)}"></span>.</p></center>'


def probability(
    favorable: int, total: int, places: int | None = None, *, symbol: str = "P"
) -> tuple[str, str]:
    if total <= 0 or not 0 <= favorable <= total:
        raise UnsupportedCondition("invalid counts for a probability space")
    value = Fraction(favorable, total)
    answer = format_answer(value) if places is None else rounded(value, places)
    steps = [
        rf"{symbol}=\frac{{N_{{\mathrm{{благ}}}}}}{{N_{{\mathrm{{общ}}}}}}",
        rf"{symbol}=\frac{{{favorable}}}{{{total}}}",
        f"{symbol}={format_latex_fraction(value)}",
    ]
    final = f"{symbol}{'=' if places is None or Fraction(answer.replace(',', '.')) == value else r'\approx '}{answer.replace(',', '{,}')}"
    steps.append(final)
    unique = [
        step
        for index, step in enumerate(steps)
        if index == 0 or step != steps[index - 1]
    ]
    return answer, "".join(line(step) for step in unique)


def finish(
    condition, answer_section, solution_section, answer: str, html: str
) -> RepairPlan:
    changes = []
    if solution_section is None or solution_section.get("html") != html:
        changes.append(rewrite(solution_section, "solution", "Решение", html))
    if not answer_matches(answer_section, answer):
        changes.append(
            rewrite(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(
        answer=answer,
        condition_html=str(condition.get("html") or ""),
        solution_html=html,
        transformations=tuple(changes),
    )
