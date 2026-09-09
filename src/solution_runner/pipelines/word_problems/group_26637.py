"""Odd-numbered bouquet purchase rule for source group 26637."""

from __future__ import annotations

import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-26637-odd-bouquet"
_CONDITION = re.compile(
    r"На день рождения полагается дарить букет из неч[её]тного числа цветов\. "
    r"(?P<flowers>[А-Яа-яЁё]+) стоят (?P<price>[1-9]\d*) рублей за штуку\. "
    r"У Вани есть (?P<budget>[1-9]\d*) рублей\. "
    r"Из какого наибольшего числа [А-Яа-яЁё]+ он может купить букет Маше на день рождения\?"
)


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 26637 template")
    price, budget = int(match["price"]), int(match["budget"])
    purchasable = budget // price
    answer = purchasable if purchasable % 2 else purchasable - 1
    if answer <= 0:
        raise UnsupportedCondition("budget cannot buy a positive odd bouquet")
    adjustment = "уже нечётное" if answer == purchasable else "чётное, поэтому возьмём на один цветок меньше"
    solution_html = (
        f"<p>Разделим {budget} на {price}: получаем {purchasable}.</p>"
        f"<p>Это число {adjustment}. Следовательно, Ваня может купить букет из {answer} цветов.</p>"
    )
    return finalize(condition, answer_section, solution_section, answer, solution_html)
