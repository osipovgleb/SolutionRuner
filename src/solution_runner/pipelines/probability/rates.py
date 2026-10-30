"""Frequency differences and subtraction of nested probability events."""

from __future__ import annotations

import re
from fractions import Fraction

from solution_runner.pipelines.core.numbers import (
    format_answer,
    format_latex_fraction,
    parse_rational,
)

from .common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    normalize,
    require_content,
)

_TEMPERATURE = re.compile(
    rf"Термометр измеряет температуру в помещении\. Вероятность того, что температура окажется выше (?P<lo>[+-]?\d+)\s*°C, равна (?P<p>{NUMBER})\. Вероятность того, что температура окажется ниже (?P<hi>[+-]?\d+)\s*°C, равна (?P<q>{NUMBER})\. Найдите вероятность того, что температура в помещении окажется в промежутке от (?P=lo)\s*°C до (?P=hi)\s*°C\."
)
_TAIL = re.compile(
    rf"Вероятность того, что на тестировании по [а-я]+ учащийся(?: (?P<person>[А-Я]\.))? (?:верно )?решит больше (?P<n>\d+) задач, равна (?P<p>{NUMBER})\. Вероятность того, что (?P<second>[А-Я]\.|учащийся) верно решит больше (?P<prev>\d+) задач, равна (?P<q>{NUMBER})\. Найдите вероятность того, что (?P<third>[А-Я]\.|учащийся) верно решит ровно (?P<target>\d+) задач\."
)
_FREQUENCY = re.compile(
    rf"Вероятность того, что новый (?P<product>[A-Za-zА-Яа-я-]+) в течение года поступит в гарантийный ремонт, равна (?P<p>{NUMBER})\. В некотором городе из (?P<n>\d+) проданных (?P<plural>[A-Za-zА-Яа-я-]+) в течение года в гарантийную мастерскую поступил[ао] (?P<m>\d+) штук(?:а|и)?\. На сколько отличается частота события «гарантийный ремонт» от его вероятности в этом городе\?"
)


def _latex(value: Fraction) -> str:
    return format_answer(value).replace(",", "{,}")


def solve(text: str) -> tuple[str, str]:
    text = normalize(text)
    if match := _TEMPERATURE.fullmatch(text):
        lo, hi = int(match["lo"]), int(match["hi"])
        p, q = parse_rational(match["p"]), parse_rational(match["q"])
        if lo >= hi or not 0 <= p <= 1 or not 0 <= q <= 1 or p + q < 1:
            raise UnsupportedCondition("inconsistent temperature probabilities")
        below, above = 1 - p, 1 - q
        value = 1 - below - above
        html = "<p>Найдём вероятности оказаться вне указанного промежутка, используя противоположные события:</p>"
        html += line(rf"P(X\le {lo})=1-{_latex(p)}={_latex(below)}")
        html += line(rf"P(X\ge {hi})=1-{_latex(q)}={_latex(above)}")
        html += "<p>События по разные стороны промежутка несовместны. Вычтем их вероятности из единицы:</p>"
        html += line(rf"P({lo}<X<{hi})=1-P(X\le {lo})-P(X\ge {hi})")
        html += line(rf"P({lo}<X<{hi})=1-{_latex(below)}-{_latex(above)}")
        html += line(rf"P({lo}<X<{hi})={_latex(value)}")
        return format_answer(value), html
    if match := _TAIL.fullmatch(text):
        if match["person"] and any(
            match[key] != match["person"] for key in ("second", "third")
        ):
            raise UnsupportedCondition(
                "the tail probabilities refer to different students"
            )
        n, prev, target = (int(match[key]) for key in ("n", "prev", "target"))
        p, q = parse_rational(match["p"]), parse_rational(match["q"])
        if n < 0 or prev != n - 1 or target != n or not 0 <= p <= q <= 1:
            raise UnsupportedCondition("nested tail events are inconsistent")
        value = q - p
        html = "<p>Число решённых задач целое. Решить больше предыдущего числа задач — значит решить ровно указанное число или больше него. Эти события несовместны:</p>"
        html += line(rf"P(X>{prev})=P(X={n})+P(X>{n})")
        html += "<p>Выразим искомую вероятность и подставим данные:</p>"
        html += line(rf"P(X={n})=P(X>{prev})-P(X>{n})")
        html += line(rf"P(X={n})={_latex(q)}-{_latex(p)}") + line(
            rf"P(X={n})={_latex(value)}"
        )
        return format_answer(value), html
    if match := _FREQUENCY.fullmatch(text):
        n, m, p = int(match["n"]), int(match["m"]), parse_rational(match["p"])
        stem = match["product"].rstrip("ьй")
        if match["plural"] not in {
            stem + ending for ending in ("ов", "ев", "ей", "ы", "и")
        }:
            raise UnsupportedCondition(
                "frequency and probability refer to different products"
            )
        if n <= 0 or not 0 <= m <= n or not 0 <= p <= 1:
            raise UnsupportedCondition("invalid empirical frequency")
        frequency = Fraction(m, n)
        value = abs(frequency - p)
        html = "<p>Частота (относительная частота) гарантийного ремонта равна отношению числа поступивших в ремонт приборов к числу проданных:</p>"
        html += line(rf"W=\frac{{{m}}}{{{n}}}") + line(
            rf"W={format_latex_fraction(frequency)}"
        )
        html += line(rf"W={_latex(frequency)}")
        html += "<p>Найдём, на сколько частота отличается от заданной вероятности; для этого берём модуль разности:</p>"
        html += line(r"\Delta=|W-p|") + line(
            rf"\Delta=|{_latex(frequency)}-{_latex(p)}|={_latex(value)}"
        )
        return format_answer(value), html
    raise UnsupportedCondition("unsupported complete probability-difference condition")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(
        context, allow_inline_latex=True
    )
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
