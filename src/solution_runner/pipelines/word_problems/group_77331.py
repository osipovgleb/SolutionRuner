"""Exact call-duration arithmetic for source group 77331."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from .common import UnsupportedCondition, decimal_latex, finalize, require_content


RULE = "word-problem-77331-mobile-call-duration"
_RUBLE = r"руб(?:ль|ля|лей)"
_CONTACT = r"[А-ЯЁ][а-яё]+"
_PREFIX = (
    rf"На (?:счету|счёте) (?P<owner>{_CONTACT}) мобильного телефона был(?:о)? "
    rf"(?P<before>\d+) {_RUBLE}, а после разговора с (?P<contact>{_CONTACT}) "
    rf"осталось (?P<after>\d+) {_RUBLE}\. "
)
_PRICE = rf"(?P<rubles>\d+) {_RUBLE} (?P<kopecks>\d+) копе(?:йка|йки|ек)"
_QUESTION = r"Сколько минут длился разговор с (?P=contact)"
_CONDITIONS = tuple(re.compile(_PREFIX + ending) for ending in (
    _QUESTION + rf", если одна минута разговора стоит {_PRICE}[?.]",
    rf"Известно, что разговор длился целое число минут, а одна минута разговора стоит {_PRICE}\. " + _QUESTION + r"\?",
))
_OWNERS = {
    "Машиного": "Маше", "Настиного": "Насте", "Юлиного": "Юле",
    "Надиного": "Наде", "Дашиного": "Даше", "Жениного": "Жене",
    "Наташиного": "Наташе", "Олиного": "Оле", "Катиного": "Кате",
    "Таниного": "Тане", "Лениного": "Лене",
}


def _line(latex: str) -> str:
    return f'<center><p><span data-inline-latex="{latex}"></span>.</p></center>'


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = next((m for pattern in _CONDITIONS if (m := pattern.fullmatch(text))), None)
    if match is None or match["owner"] not in _OWNERS:
        raise UnsupportedCondition("condition does not match group 77331 template")
    before, after, rubles, kopecks = (int(match[key]) for key in ("before", "after", "rubles", "kopecks"))
    price = rubles * 100 + kopecks
    spent = before - after
    if kopecks >= 100 or spent <= 0 or price <= 0:
        raise UnsupportedCondition("invalid balance or minute price")
    minutes, remainder = divmod(spent * 100, price)
    if remainder:
        raise UnsupportedCondition("call duration must be a whole number of minutes")
    rate = decimal_latex(Fraction(price, 100))
    solution_html = (
        f'<p>Разговор с {match["contact"]} стоил {_OWNERS[match["owner"]]}:</p>'
        + _line(f"{before}-{after}={spent}\\text{{ руб.}}")
        + "<p>Чтобы найти длительность разговора, разделим его стоимость на цену одной минуты:</p>"
        + _line(r"t=\frac{\text{стоимость разговора}}{\text{цена одной минуты}}")
        + _line(rf"t=\frac{{{spent}}}{{{rate}}}")
        + _line(rf"t=\frac{{{spent * 100}}}{{{price}}}")
        + _line(rf"t={minutes}\text{{ мин.}}")
        + f'<p>Значит, разговор с {match["contact"]} длился {minutes} минут.</p>'
    )
    return finalize(condition, answer_section, solution_section, minutes, solution_html)
