"""Monthly-travel-pass savings rule for source group 26623."""

from __future__ import annotations

import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-26623-monthly-travel-pass-savings"
_CONDITION = re.compile(
    r"Аня купила проездной билет на месяц и сделала за месяц (?P<trips>[1-9]\d*) поезд(?:ку|ки|ок)\. "
    r"Сколько рублей она сэкономила, если проездной билет(?: на месяц)? стоит (?P<pass>[1-9]\d*) рублей, "
    r"а разовая поездка — (?P<fare>[1-9]\d*) руб(?:ль|ля|лей)\?"
)


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 26623 template")
    trips, pass_cost, fare = (int(match[name]) for name in ("trips", "pass", "fare"))
    without_pass = trips * fare
    savings = without_pass - pass_cost
    solution_html = (
        f'<p>Найдём, что {trips} поездок стоили бы <span data-inline-latex="{fare}\\cdot {trips}={without_pass}"></span> рублей.</p>'
        f'<p>Значит, Аня сэкономила <span data-inline-latex="{without_pass}-{pass_cost}={savings}"></span> рублей.</p>'
    )
    return finalize(condition, answer_section, solution_section, savings, solution_html)
