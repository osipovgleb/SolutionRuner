"""Successive yearly population-change rule for source group 99565."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-99565-successive-population-change"
_CONDITION = re.compile(
    r"В (?P<first_year>20\d{2}) году в городском квартале проживало "
    r"(?P<initial>[1-9]\d*(?: \d{3})*) человек\. "
    r"В (?P<second_year>20\d{2}) году, в результате строительства новых домов, "
    r"число жителей выросло на (?P<first_percent>[1-9]\d*)%, а в (?P<third_year>20\d{2}) году (?:— )?"
    r"на (?P<second_percent>[1-9]\d*)% по сравнению с (?P=second_year) годом\. "
    r"Сколько человек стало проживать в квартале в (?P=third_year) году\?"
)


def _factor(percent: int, change: str) -> Fraction:
    return Fraction(100 + (percent if change == "увеличилось" else -percent), 100)


def _operation(change: str) -> str:
    return "+" if change == "увеличилось" else "-"


def _row(year: str, value: int, previous: int | None, percent: int | None, change: str | None) -> str:
    if previous is None:
        rendered = f'<span data-inline-latex="{value}"></span>'
    else:
        rendered = rf'<span data-inline-latex="{previous}\cdot\left(1{_operation(change or "")}\frac{{{percent}}}{{100}}\right)={value}"></span>'
    return f'<tr><td data-align="center" data-valign="middle">{year}</td><td data-align="center" data-valign="middle">{rendered}</td></tr>'


def _old_solution_html(
    second_year: str, third_year: str, initial: int, second: int, third: int, first_percent: int, second_percent: int,
) -> str:
    return (
        f'<p>В {second_year} году число жителей стало <span data-inline-latex="{initial}+0{{,}}{first_percent:02d}\\cdot {initial}={second}"></span>  '
        f'человек, а в {third_year} году число жителей стало <span data-inline-latex="{second}+0{{,}}{second_percent:02d}\\cdot {second}={third}"></span> человек.</p>'
    )


def _first_table_solution_html(
    first_year: str, second_year: str, third_year: str, initial: int, second: int, third: int, first_percent: int, second_percent: int,
) -> str:
    return (
        '<p>Если величина изменяется на <span data-inline-latex="r\\%"></span> каждый год в течение '
        '<span data-inline-latex="n"></span> лет, её можно найти по формуле '
        '<span data-inline-latex="S\\left(1\\pm\\frac{r}{100}\\right)^n"></span>: знак «+» используют '
        'при увеличении, знак «−» — при уменьшении.</p>'
        '<p>Здесь проценты за годы различаются, поэтому считаем последовательно.</p>'
        '<table><tbody><tr><th data-align="center">Год</th><th data-align="center">Число жителей</th></tr>'
        f'<tr><td data-align="center">{first_year}</td><td data-align="center">{initial}</td></tr>'
        f'<tr><td data-align="center">{second_year}</td><td data-align="center"><span data-inline-latex="{initial}\\cdot\\left(1+\\frac{{{first_percent}}}{{100}}\\right)={second}"></span></td></tr>'
        f'<tr><td data-align="center">{third_year}</td><td data-align="center"><span data-inline-latex="{second}\\cdot\\left(1+\\frac{{{second_percent}}}{{100}}\\right)={third}"></span></td></tr>'
        '</tbody></table>'
    )


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context, allow_inline_latex=True)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 99565 template")

    initial = int(match["initial"].replace(" ", ""))
    first_percent, second_percent = (int(match[name]) for name in ("first_percent", "second_percent"))
    first_change = "увеличилось"
    # The second clause uses a dash instead of repeating the verb, so it has
    # the same direction of change as the first clause.
    second_change = first_change
    second = Fraction(initial) * _factor(first_percent, first_change)
    third = second * _factor(second_percent, second_change)
    if second.denominator != 1 or third.denominator != 1:
        raise UnsupportedCondition("population must remain an integer")
    second_value, third_value = second.numerator, third.numerator

    solution_html = (
        '<p>Если величина изменяется на <span data-inline-latex="r\\%"></span> каждый год в течение '
        '<span data-inline-latex="n"></span> лет, её можно найти по формуле '
        '<span data-inline-latex="S\\left(1\\pm\\frac{r}{100}\\right)^n"></span>: знак «+» используют '
        'при увеличении, знак «−» — при уменьшении.</p>'
        '<p>Здесь проценты за годы различаются, поэтому считаем последовательно.</p>'
        '<table><tbody><tr><th data-align="center" data-cell-tone="source-header" data-valign="middle">Год</th>'
        '<th data-align="center" data-cell-tone="source-header" data-valign="middle">Число жителей</th></tr>'
        f'{_row(match["first_year"], initial, None, None, None)}'
        f'{_row(match["second_year"], second_value, initial, first_percent, first_change)}'
        f'{_row(match["third_year"], third_value, second_value, second_percent, second_change)}'
        '</tbody></table>'
    )
    old_solution = _old_solution_html(
        match["second_year"], match["third_year"], initial, second_value, third_value, first_percent, second_percent,
    )
    current_solution = str((solution_section or {}).get("html") or "")
    # Imported source solutions contain discretionary hyphens; compare only
    # after removing those invisible source-formatting characters.
    first_table_solution = _first_table_solution_html(
        match["first_year"], match["second_year"], match["third_year"], initial, second_value, third_value, first_percent, second_percent,
    )
    legacy_solution_html = (
        current_solution
        if current_solution.replace("\u00ad", "") in {old_solution, first_table_solution}
        else None
    )
    return finalize(
        condition, answer_section, solution_section, third_value, solution_html,
        legacy_solution_html=legacy_solution_html,
    )
