"""Bundle-promotion whole-purchase rule for source group 26626."""

from __future__ import annotations

import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-26626-bundle-promotion"
_NUMBER_WORDS = {"две": 2, "три": 3, "четыре": 4, "пять": 5}
_CONDITION = re.compile(
    r"Шоколадка стоит (?P<price>[1-9]\d*) рублей\. "
    r"В воскресенье в супермаркете действует специальное предложение: заплатив за (?P<paid>две|три|четыре|пять) шоколадки, "
    r"покупатель получает (?P<received>три|четыре|пять) \(одну в подарок\)\. "
    r"(?:(?:Какое наибольшее количество шоколадок можно получить, потратив не более )|(?:Сколько шоколадок можно получить на ))(?P<budget>[1-9]\d*) рублей в воскресенье\?"
)


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 26626 template")
    paid, received = _NUMBER_WORDS[match["paid"]], _NUMBER_WORDS[match["received"]]
    if received != paid + 1:
        raise UnsupportedCondition("promotion must give exactly one chocolate as a gift")
    price, budget = int(match["price"]), int(match["budget"])
    bought = budget // price
    gifts = (bought // paid) * (received - paid)
    total = bought + gifts
    solution_html = (
        f"<p>На {budget} рублей можно купить {bought} шоколадок по {price} рублей.</p>"
        f"<p>За каждые {paid} купленные шоколадки дают одну в подарок, поэтому в подарок дадут {gifts} шоколадок.</p>"
        f"<p>Всего можно получить {total} шоколадок.</p>"
    )
    return finalize(condition, answer_section, solution_section, total, solution_html)
