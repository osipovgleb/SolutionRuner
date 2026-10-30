"""The smallest number of independent attempts reaching a stated success level."""

import re
from fractions import Fraction

from solution_runner.pipelines.core.numbers import parse_rational

from .bernoulli import checked, fmt, result
from .common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    normalize,
    require_content,
)

_SINGLE = re.compile(
    rf"Стрелок в тире стреляет по мишени до тех пор, пока не поразит ее\. Известно, что он попадает в цель с вероятностью (?P<p>{NUMBER}) при каждом отдельном выстреле\. Какое наименьшее количество патронов нужно дать стрелку, чтобы он поразил цель с вероятностью не менее (?P<goal>{NUMBER})\?"
)
_FIRST = re.compile(
    rf"При артиллерийской стрельбе автоматическая система делает выстрел по цели\. Если цель не уничтожена, то система делает повторный выстрел\. Выстрелы повторяются до тех пор, пока цель не будет уничтожена\. Вероятность уничтожения некоторой цели при первом выстреле равна (?P<first>{NUMBER}), а при каждом последующем — (?P<p>{NUMBER})\. Сколько выстрелов потребуется для того, чтобы вероятность уничтожения цели была не менее (?P<goal>{NUMBER})\? В ответе укажите наименьшее необходимое количество выстрелов\."
)


def minimum_attempts(first, p, goal):
    checked(first)
    checked(p)
    checked(goal)
    if goal <= 0:
        raise UnsupportedCondition("the required success level must be positive")
    if first < goal and (p == 0 or (goal == 1 and p < 1)):
        raise UnsupportedCondition(
            "no finite number of attempts reaches the required success level"
        )
    n = 1
    fail = 1 - first
    previous = Fraction(1)
    # shortcut: cap a prepared expansion at 10000 attempts; use logarithmic bounds for larger models.
    while 1 - fail < goal:
        if n >= 10000:
            raise UnsupportedCondition(
                "the required attempt count exceeds the audited bound"
            )
        previous = fail
        fail *= 1 - p
        n += 1
    return n, previous, fail


def solve(text):
    text = normalize(text)
    match = _SINGLE.fullmatch(text) or _FIRST.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported complete retry-threshold condition")
    p, goal = parse_rational(match["p"]), parse_rational(match["goal"])
    first = parse_rational(match["first"]) if "first" in match.re.groupindex else p
    n, previous, fail = minimum_attempts(first, p, goal)
    q = 1 - p
    html = (
        "<p>Вероятность неудачи при первом выстреле и при каждом следующем равна:</p>"
        + line(rf"q_1=1-{fmt(first)}={fmt(1 - first)},\quad q=1-{fmt(p)}={fmt(q)}")
    )
    html += (
        "<p>Неудача после n попыток означает, что неудачны все независимые попытки. Требование «не менее» включает равенство:</p>"
        + line(r"P_n=1-q_1q^{n-1}")
        + line(rf"q_1q^{{n-1}}\le 1-{fmt(goal)}={fmt(1 - goal)}")
    )
    html += (
        "<p>Найдём соседние значения вероятности, между которыми впервые достигается требуемый уровень:</p>"
        + line(rf"P_{{{n - 1}}}={fmt(1 - previous)}<{fmt(goal)}")
        + line(rf"P_{{{n}}}={fmt(1 - fail)}\ge {fmt(goal)}")
    )
    html += "<p>Решение по действиям. После каждого промаха умножаем вероятность оставаться без успеха на q:</p>"
    shown = list(range(1, n + 1)) if n <= 12 else [1, 2, 3, n - 1, n]
    for j in shown:
        residual = (1 - first) * q ** (j - 1)
        html += line(
            rf"Q_{{{j}}}={fmt(residual)},\quad P_{{{j}}}=1-Q_{{{j}}}={fmt(1 - residual)}"
        )
    html += "<p>Можно также сложить вероятности первого успеха на каждой из попыток. Эти события несовместны:</p>"
    html += line("P_n=p_1" if n == 1 else r"P_n=p_1+(1-p_1)p\sum_{j=0}^{n-2}q^j")
    html += line(rf"P_{{{n}}}={fmt(1 - fail)}")
    return result(Fraction(n), html, symbol="n")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
