"""Fail-closed currency-purchase-and-rounding planner for base-EGE group 77334.

The group has one audited verbal template.  Parsing intentionally accepts no
nearby wording: a task is changed only after its complete condition and its
plain ``<p>`` markup pass the template gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, parse_rational


RULE = "word-problem-77334-currency-purchase-rounding"

_CONDITION = re.compile(
    r"В обменном пункте 1 гривна стоит "
    r"(?P<rubles>[1-9]\d*) (?P<rubles_word>рубль|рубля|рублей) "
    r"(?P<kopecks>\d{2}) копеек\. "
    r"Отдыхающие обменяли рубли на гривны и купили "
    r"(?P<purchase>[А-Яа-яЁё -]+|[А-Яа-яЁё -]*[1-9]\d* кг[А-Яа-яЁё -]*) "
    r"по цене (?P<price>[1-9]\d*) (?P<hryvnia_word>гривна|гривны|гривен) за 1 кг\. "
    r"Во сколько рублей обошлась им эта покупка\? "
    r"Ответ округлите до целого числа\."
)
_WEIGHT = re.compile(r"(?<!\d)(?P<weight>[1-9]\d*) кг")


class UnsupportedCondition(ValueError):
    """Raised before any mutation when the condition is not the audited form."""


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    condition_html: str
    solution_html: str
    transformations: tuple[dict[str, Any], ...] = ()


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [
        section for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    target = str((section or {}).get("transformation_target_id") or "")
    if not target:
        target = f"section:{key}"
    return {
        "transformation_target_id": target,
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _visible_condition(condition_html: str) -> str:
    """Accept exactly one plain paragraph, then return normalized visible text."""

    soup = BeautifulSoup(condition_html, "html.parser")
    paragraphs = soup.find_all("p")
    if len(paragraphs) != 1 or paragraphs[0].attrs or paragraphs[0].find(True):
        raise UnsupportedCondition("condition must be one plain paragraph")
    if any(node.name not in (None, "p") for node in soup.find_all(True)):
        raise UnsupportedCondition("condition markup is unsupported")
    text = paragraphs[0].get_text(" ", strip=True)
    return " ".join(text.replace("\u00ad", "").replace("\u202f", " ").split())


def _parse_condition(condition_html: str) -> tuple[int, int, int, int]:
    text = _visible_condition(condition_html)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 77334 template")
    weights = _WEIGHT.findall(match.group("purchase"))
    if len(weights) != 1:
        raise UnsupportedCondition("purchase must contain exactly one mass in kilograms")
    return (
        int(match.group("rubles")),
        int(match.group("kopecks")),
        int(weights[0]),
        int(match.group("price")),
    )


def _round_positive_half_up(value: Fraction) -> int:
    """Round the positive exact amount to a whole rouble, with halves upward."""

    whole, remainder = divmod(value.numerator, value.denominator)
    return whole + int(2 * remainder >= value.denominator)


def _latex_number(value: Fraction) -> str:
    return format_answer(value).replace(",", "{,}")


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    visible = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True)
    try:
        return parse_rational(visible) == parse_rational(expected)
    except (NumberFormatError, ValueError):
        return False


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build the minimal answer/solution repair after strict template validation."""

    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("group 77334 does not allow condition assets")

    condition, answer, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition without assets is required")

    rubles, kopecks, kilograms, price = _parse_condition(str(condition.get("html") or ""))
    rate = Fraction(rubles * 100 + kopecks, 100)
    hryvnias = kilograms * price
    amount = hryvnias * rate
    rounded = _round_positive_half_up(amount)
    rendered_answer = str(rounded)
    solution_html = (
        "<p>Сначала найдём стоимость покупки в гривнах:</p>"
        f'<center><p><span data-inline-latex="{kilograms}\\cdot {price}={hryvnias}"></span>.</p></center>'
        "<p>Переведём эту стоимость в рубли:</p>"
        f'<center><p><span data-inline-latex="{hryvnias}\\cdot {_latex_number(rate)}={_latex_number(amount)}"></span>.</p></center>'
        "<p>Округлим результат до целого числа:</p>"
        f'<center><p><span data-inline-latex="{_latex_number(amount)}\\approx {rounded}"></span>.</p></center>'
    )
    transformations: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != solution_html:
        transformations.append(_rewrite(solution, "solution", "Решение", solution_html))
    if not _answer_matches(answer, rendered_answer):
        transformations.append(_rewrite(answer, "answer", "Ответ", f"<p>{rendered_answer}</p>"))
    return RepairPlan(
        answer=rendered_answer,
        condition_html=str(condition.get("html") or ""),
        solution_html=solution_html,
        transformations=tuple(transformations),
    )
