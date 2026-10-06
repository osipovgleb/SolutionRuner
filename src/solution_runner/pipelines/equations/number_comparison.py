"""Fail-closed plans for OGE multiple-choice number comparisons."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RightTrianglePlanError


_FRACTION = re.compile(r"^\\frac\{(-?\d+)\}\{(\d+)\}$")
_DECIMAL = re.compile(r"^-?\d+(?:[,.]\d+)?$")
_BETWEEN = "заклю"  # catches the source's soft-hyphen spelling too.


class RepairPlan:
    def __init__(self, answer: str, transformations: tuple[dict[str, Any], ...]) -> None:
        self.answer = answer
        self.transformations = transformations


def _value(raw: str) -> Fraction:
    value = raw.replace(" ", "").replace("{,}", ",")
    fraction = _FRACTION.fullmatch(value)
    if fraction:
        return Fraction(int(fraction.group(1)), int(fraction.group(2)))
    if _DECIMAL.fullmatch(value):
        return Fraction(value.replace(",", "."))
    raise RightTrianglePlanError("number option is not a reviewed fraction or decimal")


def _latex(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"\\frac{{{value.numerator}}}{{{value.denominator}}}"


def _fraction_spans(soup: BeautifulSoup) -> list[Fraction]:
    values = []
    for span in soup.find_all("span", attrs={"data-inline-latex": True}):
        values.append(_value(str(span["data-inline-latex"])))
    return values


def _options(soup: BeautifulSoup) -> list[Fraction]:
    rows = soup.find_all("li") or soup.find_all("td")
    if len(rows) == 4:
        return [_value(re.sub(r"^\s*\d\)\s*", "", row.get_text("", strip=True))) for row in rows]
    text = soup.get_text(" ", strip=True).replace("\xad", "")
    values = re.findall(r"(?:^|\s)[1-4]\)\s*(.*?)(?=\s+[1-4]\)|$)", text)
    if len(values) != 4:
        raise RightTrianglePlanError("condition must contain exactly four options")
    return [_value(value) for value in values]


def _between_plan(soup: BeautifulSoup) -> tuple[str, str]:
    bounds = _fraction_spans(soup)[:2]
    options = _options(soup)
    if len(bounds) != 2:
        raise RightTrianglePlanError("comparison condition must state two bounds")
    lower, upper = sorted(bounds)
    matches = [index for index, value in enumerate(options, start=1) if lower < value < upper]
    if len(matches) != 1:
        raise RightTrianglePlanError("comparison condition does not select one option")
    answer = str(matches[0])
    chosen = options[matches[0] - 1]
    return answer, (
        f'<p>Сравним выбранное число с границами промежутка.</p>'
        f'<center><p><span data-inline-latex="{_latex(lower)}&lt;{_latex(chosen)}&lt;{_latex(upper)}"></span>.</p></center>'
        f'<p>Только вариант {answer} лежит строго между данными числами.</p>'
    )


def _point_plan(soup: BeautifulSoup) -> tuple[str, str]:
    options = _fraction_spans(soup)
    if len(options) != 4:
        raise RightTrianglePlanError("number-line condition must contain four fraction options")
    text = soup.get_text(" ", strip=True).replace(" ", " ").replace("\xad", "").lower()
    interval = re.search(r"районе\s+(\d+[,.]\d+)\s*[–-]\s*(\d+[,.]\d+)", text)
    tick = re.search(r"над\s+де[лл]ением\s+(\d+[,.]\d+)", text)
    if interval:
        low, high = (Fraction(value.replace(",", ".")) for value in interval.groups())
        matches = [index for index, value in enumerate(options, start=1) if low <= value <= high]
    elif tick:
        point = Fraction(tick.group(1).replace(",", "."))
        distance = min(abs(value - point) for value in options)
        matches = [index for index, value in enumerate(options, start=1) if abs(value - point) == distance]
    else:
        raise RightTrianglePlanError("number-line position is unavailable")
    if len(matches) != 1:
        raise RightTrianglePlanError("number-line condition does not select one option")
    answer = str(matches[0])
    return answer, (
        f'<p>По положению точки A на числовой прямой выбираем ближайшую из предложенных дробей.</p>'
        f'<center><p><span data-inline-latex="A={_latex(options[matches[0] - 1])}"></span>.</p></center>'
        f'<p>Это вариант {answer}.</p>'
    )


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition is required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    visible = soup.get_text(" ", strip=True).replace("\xad", "").lower()
    if _BETWEEN in visible:
        answer, solution = _between_plan(soup)
    elif "точкой a" in visible:
        answer, solution = _point_plan(soup)
    else:
        raise RightTrianglePlanError("condition is not a reviewed number comparison")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes = [
        _section_transformation(solution_section, "solution", "Решение", solution),
    ]
    if BeautifulSoup(str((answer_section or {}).get("html") or ""), "html.parser").get_text("", strip=True) != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer, tuple(changes))
