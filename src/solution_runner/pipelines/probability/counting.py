"""Uniform selection using audited totals, complements and quality counts."""

from __future__ import annotations

import re

from .arrangement_counts import parse as arrangement_counts
from .circular_counts import parse as circular_counts
from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    probability,
    require_content,
    rounding,
)
from .country_counts import parse as country_counts
from .inventory_counts import parse as inventory_counts
from .named_counts import parse as named_counts
from .quality_counts import parse as quality_counts
from .schedule_counts import parse as schedule_counts
from .selection_counts import parse as selection_counts
from .service_counts import parse as service_counts

_BOOKS = re.compile(
    rf'В сборнике билетов по [А-Яа-я ]+ всего (?P<n>\d+) билетов, в (?P<m>{COUNT}) из них встречается вопрос (?P<topic>о грибах|о Великой Отечественной войне|по теме «[^«»]+»|по теме "[^"]+")\. (?P<question>.+)'
)
_EXAM = re.compile(
    r"(?:На экзамен вынесено|На экзамене) (?P<n>\d+) (?P<kind>вопросов|билетов)[,.] [А-Я][а-я]+ не выучил (?P<m>\d+) из них\. Найдите вероятность того, что ему попадется выученный (?P<target>вопрос|билет)\."
)


def _books(text):
    match = _BOOKS.fullmatch(text)
    if match is None:
        return None
    n, included, topic = int(match["n"]), count(match["m"]), match["topic"]
    question = match["question"].removeprefix(
        "На экзамене школьнику достается один случайно выбранный билет из этого сборника. "
    )
    positive = {
        f"Найдите вероятность того, что в случайно выбранном на экзамене билете школьнику достанется вопрос {topic}.",
        f"Найдите вероятность того, что в этом билете будет вопрос {topic}.",
    }
    negative = {
        f"Найдите вероятность того, что в случайно выбранном на экзамене билете школьнику не достанется {word} {topic}."
        for word in ("вопрос", "вопроса")
    }
    negative.add(
        f"Найдите вероятность того, что в этом билете не будет вопроса {topic}."
    )
    if question not in positive | negative:
        raise UnsupportedCondition("the ticket question is not the audited event")
    favorable = included if question in positive else n - included
    html = "<p>Все билеты равновозможны. "
    html += (
        "Нужный вопрос содержится в указанном числе билетов:</p>"
        if question in positive
        else "Исключим билеты, в которых встречается указанный вопрос:</p>"
    )
    html += line(rf"N_{{\mathrm{{общ}}}}={n}")
    html += line(
        rf"N_{{\mathrm{{благ}}}}={included}"
        if question in positive
        else rf"N_{{\mathrm{{благ}}}}={n}-{included}={favorable}"
    )
    return n, favorable, html, "P"


def _exam(text):
    match = _EXAM.fullmatch(text)
    if match is None:
        return None
    n, unlearned = int(match["n"]), int(match["m"])
    if (match["kind"] == "вопросов") != (match["target"] == "вопрос"):
        raise UnsupportedCondition("the exam question and total use different objects")
    html = "<p>Чтобы найти число выученных вопросов или билетов, вычтем невыученные из общего количества:</p>"
    html += line(rf"N_{{\mathrm{{общ}}}}={n}") + line(
        rf"N_{{\mathrm{{благ}}}}={n}-{unlearned}={n - unlearned}"
    )
    return n, n - unlearned, html, "P"


def solve(text):
    text, places = rounding(normalize(text))
    for parser in (
        arrangement_counts,
        circular_counts,
        _books,
        _exam,
        quality_counts,
        selection_counts,
        inventory_counts,
        named_counts,
        service_counts,
        country_counts,
        schedule_counts,
    ):
        result = parser(text)
        if result is not None:
            n, m, html, symbol = result
            answer, calculation = probability(m, n, places, symbol=symbol)
            return (
                answer,
                html
                + "<p>Разделим число подходящих исходов на общее количество:</p>"
                + calculation,
            )
    raise UnsupportedCondition("unsupported complete counting condition")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(
        context, allow_inline_latex=True
    )
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
