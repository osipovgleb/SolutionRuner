"""Yearly refrigerator-price decline rule for source group 99569."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-99569-refrigerator-price-decline"
_CONDITION = re.compile(
    r"Цена холодильника в магазине ежегодно уменьшается на одно и то же число процентов от предыдущей цены\. "
    r"Определите, на сколько процентов каждый год уменьшалась цена холодильника, если, выставленный на продажу за "
    r"(?P<initial>[1-9]\d*(?: \d{3})*) рублей, через (?P<years>два|три|четыре) года был продан за "
    r"(?P<final>[1-9]\d*(?: \d{3})*) рубл(?:ей|я|ь)\."
)
_YEARS = {"два": 2, "три": 3, "четыре": 4}


def _integer_nth_root(value: int, degree: int) -> int | None:
    """Return the exact non-negative integer root, or None."""

    low, high = 0, value + 1
    while low + 1 < high:
        middle = (low + high) // 2
        if middle**degree <= value:
            low = middle
        else:
            high = middle
    return low if low**degree == value else None


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context, allow_inline_latex=True)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 99569 template")

    initial = int(match["initial"].replace(" ", ""))
    final = int(match["final"].replace(" ", ""))
    years = _YEARS[match["years"]]
    ratio = Fraction(final, initial)
    numerator_root = _integer_nth_root(ratio.numerator, years)
    denominator_root = _integer_nth_root(ratio.denominator, years)
    if numerator_root is None or denominator_root is None:
        raise UnsupportedCondition("price ratio is not an exact yearly integer-percent power")

    yearly_factor = Fraction(numerator_root, denominator_root)
    decrease = (1 - yearly_factor) * 100
    if not 0 < yearly_factor < 1 or decrease.denominator != 1:
        raise UnsupportedCondition("yearly decrease is not a positive integer percent")
    answer = decrease.numerator

    solution_html = (
        '<p>Пусть цена холодильника ежегодно уменьшается на <span data-inline-latex="p\\%"></span>. '
        f'Тогда через {years} года цена составит '
        f'<span data-inline-latex="{initial}\\left(1-\\frac{{p}}{{100}}\\right)^{{{years}}}"></span> рублей. По условию:</p>'
        '<center><p><span data-inline-latex="'
        f'{initial}\\left(1-\\frac{{p}}{{100}}\\right)^{{{years}}}={final}'
        '"></span>.</p></center>'
        '<p>Разделим обе части равенства на первоначальную цену и сократим дробь:</p>'
        '<center><p><span data-inline-latex="'
        f'\\left(1-\\frac{{p}}{{100}}\\right)^{{{years}}}=\\frac{{{final}}}{{{initial}}}=\\frac{{{ratio.numerator}}}{{{ratio.denominator}}}=\\frac{{{numerator_root}^{years}}}{{{denominator_root}^{years}}}'
        '"></span>.</p></center>'
        '<p>Так как <span data-inline-latex="1-\\frac{p}{100}>0"></span>, получаем:</p>'
        '<center><p><span data-inline-latex="'
        f'1-\\frac{{p}}{{100}}=\\frac{{{numerator_root}}}{{{denominator_root}}}\\iff '
        f'\\frac{{p}}{{100}}=1-\\frac{{{numerator_root}}}{{{denominator_root}}}=\\frac{{{decrease.numerator}}}{{100}}\\iff p={answer}'
        '"></span>.</p></center>'
        f'<p>Значит, цена ежегодно уменьшалась на <span data-inline-latex="{answer}\\%"></span>.</p>'
    )
    return finalize(
        condition, answer_section, solution_section, answer, solution_html,
        rewrite_existing_solution=True,
    )
