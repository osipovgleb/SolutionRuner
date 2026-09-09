"""Shirts-versus-jacket percentage rule for source group 99567."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-99567-shirt-jacket-percent"
_NUMBERS = {
    "одна": 1, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
    "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
    "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
    "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
    "двадцать": 20,
}
_GENITIVE = {
    "одна": "одной", "две": "двух", "три": "трёх", "четыре": "четырёх", "пять": "пяти",
    "шесть": "шести", "семь": "семи", "восемь": "восьми", "девять": "девяти", "десять": "десяти",
    "одиннадцать": "одиннадцати", "двенадцать": "двенадцати", "тринадцать": "тринадцати",
    "четырнадцать": "четырнадцати", "пятнадцать": "пятнадцати", "шестнадцать": "шестнадцати",
    "семнадцать": "семнадцати", "восемнадцать": "восемнадцати", "девятнадцать": "девятнадцати",
    "двадцать": "двадцати",
}
_CONDITION = re.compile(
    r"(?P<first_word>[А-Яа-яЁё]+)\s*одинаков(?:ые|ых) рубаш(?:ка|ки|ек) дешевле куртки на (?P<discount>[1-9]\d*)%\. "
    r"На сколько процентов (?P<second_word>[А-Яа-яЁё]+) таки(?:е|х) же рубаш(?:ка|ки|ек) дороже куртки\?"
)


def _number(word: str) -> int:
    try:
        return _NUMBERS[word.lower()]
    except KeyError as exc:
        raise UnsupportedCondition(f"unsupported shirt count: {word}") from exc


def _genitive(word: str) -> str:
    try:
        return _GENITIVE[word.lower()]
    except KeyError as exc:
        raise UnsupportedCondition(f"unsupported shirt count: {word}") from exc


def _latex(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 99567 template")

    first, second, discount = _number(match["first_word"]), _number(match["second_word"]), int(match["discount"])
    first_word, second_word = _genitive(match["first_word"]), _genitive(match["second_word"])
    first_cost = 100 - discount
    one_cost = Fraction(first_cost, first)
    second_cost = second * one_cost
    answer = second_cost - 100
    if answer.denominator != 1:
        raise UnsupportedCondition("the requested percentage must be an integer")
    answer_value = answer.numerator

    solution_html = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        f'<p>Стоимость {first_word} рубашек составляет <span data-inline-latex="{first_cost}\\%"></span> стоимости куртки. '
        f'Значит, стоимость одной рубашки составляет <span data-inline-latex="\\frac{{{first_cost}}}{{{first}}}\\%={_latex(one_cost)}\\%"></span> стоимости куртки. '
        f'Поэтому стоимость {second_word} рубашек составляет <span data-inline-latex="{second}\\cdot{_latex(one_cost)}\\%={_latex(second_cost)}\\%"></span> стоимости куртки. '
        f'Это превышает стоимость куртки на <span data-inline-latex="{_latex(second_cost)}\\%-100\\%={answer_value}\\%"></span>.</p>'
        '</section>'
        '<section data-content-kind="solution" data-solution-title="Приведем другое решение.">'
        f'<p>Примем стоимость куртки за <span data-inline-latex="100"></span> рублей. Тогда {first_word} рубашек стоят '
        f'<span data-inline-latex="100-{discount}={first_cost}"></span> рублей, а одна рубашка стоит '
        f'<span data-inline-latex="\\frac{{{first_cost}}}{{{first}}}={_latex(one_cost)}"></span> рубля.</p>'
        f'<p>Стоимость {second_word} рубашек равна <span data-inline-latex="{second}\\cdot{_latex(one_cost)}={_latex(second_cost)}"></span> рублей. '
        f'Она больше стоимости куртки на <span data-inline-latex="{_latex(second_cost)}-100={answer_value}"></span> рублей, то есть на <span data-inline-latex="{answer_value}\\%"></span>.</p>'
        '</section>'
    )
    return finalize(
        condition, answer_section, solution_section, answer_value, solution_html,
        rewrite_existing_solution=True,
    )
