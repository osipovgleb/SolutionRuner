"""Completely filled bookcase rule for source group 26641."""

from __future__ import annotations

import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-26641-full-bookcases"
_COURSES = {"одного": 1, "двух": 2, "трёх": 3, "трех": 3, "четырёх": 4, "четырех": 4, "пяти": 5, "шести": 6}
_CONDITION = re.compile(
    r"В университетскую библиотеку привезли новые учебники по (?P<subject>[А-Яа-яЁё -]+) для (?P<courses>[1-9]\d*(?:-[1-9]\d*)?|[А-Яа-яЁё]+) курсов,? "
    r"по (?P<per_course>[1-9]\d*) штук для каждого курса\. Все книги одинаковы по размеру\. "
    r"В книжном шкафу (?P<shelves>[1-9]\d*) полок, на каждой полке помещается (?P<per_shelf>[1-9]\d*) учебников\. "
    r"Сколько шкафов можно (?:полностью|целиком) заполнить новыми учебниками\?"
)


def _course_count(value: str) -> int:
    if value in _COURSES:
        return _COURSES[value]
    if re.fullmatch(r"[1-9]\d*", value):
        return int(value)
    range_match = re.fullmatch(r"([1-9]\d*)-([1-9]\d*)", value)
    if range_match is not None:
        first, last = map(int, range_match.groups())
        if first <= last:
            return last - first + 1
    raise UnsupportedCondition("unsupported course count")


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 26641 template")
    courses = _course_count(match["courses"])
    per_course, shelves, per_shelf = (int(match[name]) for name in ("per_course", "shelves", "per_shelf"))
    books, capacity = courses * per_course, shelves * per_shelf
    full = books // capacity
    legacy_solution_html = (
        f"<p>Всего привезли {per_course}\\cdot {courses}={books} учебников.</p>"
        f"<p>В одном книжном шкафу помещается {per_shelf}\\cdot {shelves}={capacity} учебников.</p>"
        f"<p>Разделим {books} на {capacity}: полностью можно заполнить {full} шкафов.</p>"
    )
    noun = "шкаф" if full == 1 else "шкафа" if 2 <= full <= 4 else "шкафов"
    solution_html = (
        f'<p>Всего привезли <span data-inline-latex="{per_course}\\cdot {courses}={books}"></span> учебников. '
        f'В книжном шкафу помещается <span data-inline-latex="{per_shelf}\\cdot {shelves}={capacity}"></span> учебников. '
        f'Разделим <span data-inline-latex="\\frac{{{books}}}{{{capacity}}}"></span>.</p>'
        f"<p>Значит, полностью можно заполнить {full} {noun}.</p>"
    )
    return finalize(
        condition, answer_section, solution_section, full, solution_html,
        legacy_solution_html=legacy_solution_html,
    )
