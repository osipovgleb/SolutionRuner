"""Complete statements for summed rates, remaining work and relative rates."""

import re

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from ..probability.common import count
from .common import UnsupportedCondition
from .motion_questions import DURATION, Question, duration

_MINUTES = r"минут(?:у|ы)?"
_DAYS = r"д(?:ень|ня|ней)"
_COUNT = rf"(?:{VALUE}|два|три|четыре)"
_NAME = r"[А-Я][а-я]+"
_TARGET_VOLUME = rf" Сколько минут эти два насоса должны работать совместно, чтобы перекачать (?P<target>{VALUE}) литр(?:а|ов)? воды\?"
PATTERNS = {
    "work_equal_join": rf"Каждый из двух рабочих одинаковой квалификации может выполнить заказ за (?P<solo>{DURATION})\. Через (?P<delay>{DURATION}) после того, как один из них приступил к выполнению заказа, к нему присоединился второй рабочий, и работу над заказом они довели до конца уже вместе\. Сколько часов потребовалось на выполнение всего заказа\?",
    "work_sum_two": rf"Один мастер может выполнить заказ за (?P<t1>{DURATION}), а другой — за (?P<t2>{DURATION})\. За сколько часов выполнят заказ оба мастера, работая вместе\?",
    "work_sum_three": rf"Первый насос наполняет бак за (?P<t1>{DURATION}), второй — за (?P<t2>{DURATION}), а третий — за (?P<t3>{DURATION})\. За сколько минут наполнят бак три насоса, работая одновременно\?",
    "work_known_girl": rf"(?P<first>{_NAME}) и (?P<second>{_NAME}) пропалывают грядку за (?P<joint>{VALUE}) {_MINUTES}, а одна (?P<known_name>{_NAME}) — за (?P<known>{VALUE}) {_MINUTES}\. За сколько минут пропалывает грядку одна (?P<asked_name>{_NAME})\?",
    "work_known_pipe": rf"Две трубы наполняют бассейн за (?P<joint>{DURATION}), а одна первая труба наполняет бассейн за (?P<known>{DURATION})\. За сколько часов наполняет бассейн одна вторая труба\?",
    "known_pipe_reversed": rf"Первая труба заполняет бассейн за (?P<known>{DURATION}), а две трубы вместе — за (?P<joint>{DURATION})\. За сколько часов заполняет бассейн одна вторая труба\?",
    "work_gap_pipes": rf"Первая труба наполняет резервуар на (?P<gap>{VALUE}) {_MINUTES} дольше, чем вторая\. Обе трубы(?:, работая одновременно,)? наполняют этот же резервуар за (?P<joint>{VALUE}) {_MINUTES}\. За сколько минут наполняет этот резервуар одна вторая труба\?",
    "work_gap_filter": rf"Два промышленных фильтра, работая одновременно, очищают цистерну воды за (?P<joint>{VALUE}) {_MINUTES}\. Определите, за сколько минут второй фильтр очистит цистерну воды, работая отдельно, если известно, что он сделает это на (?P<gap>{VALUE}) {_MINUTES} быстрее, чем первый\.",
    "work_gap_printer": rf"При двух одновременно работающих принтерах расход бумаги составляет 1 пачку за (?P<joint>{VALUE}) {_MINUTES}\. Определите, за сколько минут израсходует пачку бумаги первый принтер, если известно, что он сделает это на (?P<gap>{VALUE}) {_MINUTES} быстрее, чем второй\.",
    "work_measured_sum": rf"Первый садовый насос перекачивает (?P<volume>{VALUE}) литр(?:а|ов)? воды за (?P<t1>{DURATION}), второй насос перекачивает тот же объем воды за (?P<t2>{DURATION})\."
    + _TARGET_VOLUME,
    "measured_assist": rf"В помощь садовому насосу, перекачивающему (?P<volume>{VALUE}) литр(?:а|ов)? воды за (?P<t1>{DURATION}), подключили второй насос, перекачивающий тот же объем воды за (?P<t2>{DURATION})\."
    + _TARGET_VOLUME,
    "work_ratio_workers": rf"Двое рабочих, работая вместе, могут выполнить работу за (?P<joint>{VALUE}) {_DAYS}\. За сколько дней, работая отдельно, выполнит эту работу первый рабочий, если он за (?P<span1>{_COUNT}) {_DAYS} выполняет такую же часть работы, какую второй — за (?P<span2>{_COUNT}) {_DAYS}\?",
    "work_apprentice": rf"Заказ по изготовлению деталей ученик токаря может выполнить за (?P<apprentice>{DURATION}), а токарь — за (?P<master>{DURATION})\. Ученик начал выполнять такой заказ\. Через какое время после начала выполнения заказа учеником нужно начать работу токарю, чтобы в этом заказе деталей, изготовленных учеником, было в (?P<ratio>{_COUNT}) раза больше деталей, изготовленных токарем\? Ответ дайте в часах\.",
}
TIME_FIELDS = {
    "work_equal_join": ("solo", "delay"),
    "work_sum_two": ("t1", "t2"),
    "work_sum_three": ("t1", "t2", "t3"),
    "work_known_pipe": ("joint", "known"),
    "work_measured_sum": ("t1", "t2"),
    "work_apprentice": ("apprentice", "master"),
}
ALIASES = {
    "known_pipe_reversed": "work_known_pipe",
    "measured_assist": "work_measured_sum",
}


def number(text):
    return scalar(text) if re.fullmatch(VALUE, text) else sp.Integer(count(text))


def prepare(kind, data):
    kind = ALIASES.get(kind, kind)
    fields = TIME_FIELDS.get(kind, ())
    times = {key: duration(data[key]) for key in fields}
    scale = 60 if kind in {"work_sum_three", "work_measured_sum"} else 1
    values = {key: time.total * scale for key, time in times.items()}
    words = {"first", "second", "known_name", "asked_name"}
    values.update(
        (key, number(value))
        for key, value in data.items()
        if key not in set(fields) | words
    )
    if any(value <= 0 for value in values.values()):
        raise UnsupportedCondition(
            "positive work times, volumes and ratios are required"
        )
    if kind == "work_known_girl":
        first, second, known, asked = (
            data[key] for key in ("first", "second", "known_name", "asked_name")
        )
        if first == second or {known, asked} != {first, second}:
            raise UnsupportedCondition(
                "the known and requested gardeners must be distinct named participants"
            )
        values.update(known_name=known, asked_name=asked)
    return Question(kind, values, times)


def parse(text):
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            return prepare(kind, match.groupdict())
    from .work_extra_questions import parse as extra

    return extra(text)
