"""Maximum whole-item purchase rule for source group 506389."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from .common import UnsupportedCondition, decimal_latex, finalize, mixed_latex, require_content


RULE = "word-problem-506389-whole-item-purchase"
_CONDITION = re.compile(
    r"Сырок стоит (?P<rubles>[1-9]\d*) (?:рубль|рубля|рублей)(?: (?P<kopecks>\d{2}) копеек)?\. "
    r"Какое наибольшее число сырков можно купить на (?P<budget>[1-9]\d*) рублей\?"
)


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 506389 template")
    price = Fraction(int(match["rubles"]) * 100 + int(match["kopecks"] or 0), 100)
    budget = int(match["budget"])
    quotient = Fraction(budget, 1) / price
    maximum = quotient.numerator // quotient.denominator
    solution_html = (
        f"<p>Разделим {budget} рублей на стоимость одного сырка:</p>"
        f'<center><p><span data-inline-latex="\\frac{{{budget}}}{{{decimal_latex(price)}}}={mixed_latex(quotient)}"></span>.</p></center>'
        f"<p>Значит, на {budget} рублей можно купить {maximum} сырков.</p>"
    )
    return finalize(condition, answer_section, solution_section, maximum, solution_html)
