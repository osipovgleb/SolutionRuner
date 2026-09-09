"""Company-capital profit-share rule for source group 99570."""

from __future__ import annotations

from fractions import Fraction
from html import escape
import re
from typing import Any

from .common import UnsupportedCondition, decimal_latex, finalize, require_content
from solution_runner.pipelines.core.numbers import NumberFormatError


RULE = "word-problem-99570-company-capital-profit-tables"
_CONDITION = re.compile(
    r"(?P<first>[А-ЯЁ][а-яё]+), (?P<second>[А-ЯЁ][а-яё]+), (?P<third>[А-ЯЁ][а-яё]+) и (?P<fourth>[А-ЯЁ][а-яё]+) "
    r"учредили компанию с уставным капиталом (?P<capital>[1-9]\d*(?: \d{3})*) рублей\. "
    r"(?P=first) внес (?P<first_percent>[1-9]\d*(?:[,.]\d+)?)% уставного капитала, "
    r"(?P=second) — (?P<second_rubles>[1-9]\d*(?: \d{3})*) рублей, "
    r"(?P=third) — (?P<third_fraction>0[,.]\d+) уставного капитала, "
    r"а оставшуюся часть капитала внес (?P=fourth)\. "
    r"Учредители договорились делить ежегодную прибыль пропорционально внесенному в уставной капитал вкладу\. "
    r"Какая сумма от прибыли (?P<profit>[1-9]\d*(?: \d{3})*) рублей причитается (?P<asked>[А-ЯЁ][а-яё]+)\? Ответ дайте в рублях\."
)


def _fraction(text: str) -> Fraction:
    return Fraction(text.replace(",", "."))


def _latex_fraction(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _percent(value: Fraction) -> str:
    """Prefer a decimal percentage; keep an exact fraction if it repeats."""

    try:
        return decimal_latex(value)
    except NumberFormatError:
        return _latex_fraction(value)


def _cell(value: str) -> str:
    return f'<td data-align="center" data-valign="middle">{value}</td>'


def _math(value: str | int) -> str:
    return f'<span data-inline-latex="{value}"></span>'


def _table(names: tuple[str, str, str, str], rows: tuple[tuple[str, tuple[str, str, str, str, str]], ...]) -> str:
    headers = "".join(
        f'<th data-align="center" data-cell-tone="source-header" data-valign="middle">{escape(name)}</th>'
        for name in ("", *names, "Всего")
    )
    body = "".join(
        '<tr>' + _cell(f'<b>{title}</b>') + "".join(_cell(value) for value in values) + '</tr>'
        for title, values in rows
    )
    return f'<table><tbody><tr>{headers}</tr>{body}</tbody></table>'


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context, allow_inline_latex=True)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 99570 template")

    names = tuple(match[name] for name in ("first", "second", "third", "fourth"))
    capital = int(match["capital"].replace(" ", ""))
    profit = int(match["profit"].replace(" ", ""))
    shares = (
        _fraction(match["first_percent"]) / 100,
        Fraction(int(match["second_rubles"].replace(" ", "")), capital),
        _fraction(match["third_fraction"]),
    )
    residual = 1 - sum(shares)
    if not 0 < residual < 1:
        raise UnsupportedCondition("residual contribution must be a positive proper fraction")
    all_shares = (*shares, residual)
    rubles = tuple(share * capital for share in all_shares)
    profits = tuple(share * profit for share in all_shares)
    if any(value.denominator != 1 for value in (*rubles, *profits)):
        raise UnsupportedCondition("every contribution and profit share must be integral")
    answer = profits[3].numerator

    source_fraction = match["third_fraction"].replace(",", "{,}")
    initial_table = _table(names, (
        ("Рубли", ("—", _math(rubles[1].numerator), "—", "—", _math(capital))),
        ("Дроби", ("—", "—", f'<span data-inline-latex="{source_fraction}"></span>', "—", _math(1))),
        ("Проценты", (f'<span data-inline-latex="{match["first_percent"].replace(",", "{,")}\\%"></span>', "—", "—", "—", '<span data-inline-latex="100\\%"></span>')),
        ("Прибыль", ("—", "—", "—", "—", _math(profit))),
    ))
    percent_calculations = (
        '<p>Вычислим доли учредителей в процентах:</p>'
        f'<p><b>{escape(names[0])}:</b> <span data-inline-latex="{match["first_percent"].replace(",", "{,")}\\%"></span> — дано по условию. Следовательно, <nobr><span data-inline-latex="{_percent(all_shares[0] * 100)}\\%\\cdot{profit}={profits[0].numerator}"></span></nobr>.</p>'
        f'<p><b>{escape(names[1])}:</b> <nobr><span data-inline-latex="\\frac{{{rubles[1].numerator}}}{{{capital}}}\\cdot100\\%={_percent(all_shares[1] * 100)}\\%"></span></nobr>. Следовательно, <nobr><span data-inline-latex="{_percent(all_shares[1] * 100)}\\%\\cdot{profit}={profits[1].numerator}"></span></nobr>.</p>'
        f'<p><b>{escape(names[2])}:</b> <nobr><span data-inline-latex="{source_fraction}\\cdot100\\%={_percent(all_shares[2] * 100)}\\%"></span></nobr>. Следовательно, <nobr><span data-inline-latex="{_percent(all_shares[2] * 100)}\\%\\cdot{profit}={profits[2].numerator}"></span></nobr>.</p>'
        f'<p><b>{escape(names[3])}:</b> <nobr><span data-inline-latex="100\\%-{_percent(all_shares[0] * 100)}\\%-{_percent(all_shares[1] * 100)}\\%-{_percent(all_shares[2] * 100)}\\%={_percent(residual * 100)}\\%"></span></nobr>. Следовательно, <nobr><span data-inline-latex="{_percent(all_shares[3] * 100)}\\%\\cdot{profit}={profits[3].numerator}"></span></nobr>.</p>'
    )
    percent_values = (
        f'<span data-inline-latex="{match["first_percent"].replace(",", "{,")}\\%"></span>',
        f'<span data-inline-latex="{_percent(all_shares[1] * 100)}\\%"></span>',
        f'<span data-inline-latex="{_percent(all_shares[2] * 100)}\\%"></span>',
        f'<span data-inline-latex="{_percent(residual * 100)}\\%"></span>',
        '<span data-inline-latex="100\\%"></span>',
    )
    full_table = _table(names, (
        ("Рубли", ("—", _math(rubles[1].numerator), "—", "—", _math(capital))),
        ("Дроби", ("—", "—", f'<span data-inline-latex="{source_fraction}"></span>', "—", _math(1))),
        ("Проценты", percent_values),
        ("Прибыль", tuple(_math(value.numerator) for value in profits) + (_math(profit),)),
    ))
    solution_html = (
        '<p>Сначала заполним таблицу данными из условия.</p>' + initial_table +
        percent_calculations +
        '<p>Заполним вторую таблицу. Прибыль распределяется в тех же долях.</p>' + full_table +
        f'<p>Значит, <b>{escape(names[3])}</b> причитается <span data-inline-latex="{answer}"></span> рублей.</p>'
    )
    return finalize(condition, answer_section, solution_section, answer, solution_html, rewrite_existing_solution=True)
