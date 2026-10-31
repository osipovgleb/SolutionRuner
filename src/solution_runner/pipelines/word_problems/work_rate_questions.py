"""Whole worker and pipe conditions with role-specific job volumes and units."""

import re

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .motion_questions import DURATION, Question, duration

_DETAIL = r"детал(?:ь|и|ей)"
_LITRE = r"литр(?:а|ов)?"
_ORDER = rf"Заказ на (?P<amount>{VALUE}) {_DETAIL} первый рабочий выполняет на (?P<delay>{DURATION}) быстрее, чем второй\. "
PATTERNS = {
    "same_worker": _ORDER
    + rf"Сколько деталей за час изготавливает (?P<who>первый|второй) рабочий, если известно, что (?P<faster>первый|он) за час изготавливает на (?P<gap>{VALUE}) {_DETAIL} больше(?P<comparison> второго)?\?",
    "different_workers": rf"На изготовление (?P<fast_amount>{VALUE}) {_DETAIL} первый рабочий (?:тратит|затрачивает) на (?P<delay>{DURATION}) меньше, чем второй рабочий на изготовление (?P<slow_amount>{VALUE}) (?:таких же )?{_DETAIL}\. Известно, что первый рабочий за час делает на (?P<gap>{VALUE}) {_DETAIL} больше, чем второй\. Сколько деталей (?:в|за) час делает (?P<who>первый|второй) рабочий\?",
    "pipes": rf"Первая труба пропускает на (?P<gap>{VALUE}) {_LITRE} воды в минуту меньше, чем вторая\. Сколько литров воды в минуту пропускает (?P<who>первая|вторая) труба, если резервуар объемом (?P<amount>{VALUE}) {_LITRE} она заполняет на (?P<delay>{VALUE}) минут(?:у|ы)? (?P<comparison>дольше|быстрее), чем (?P<other>первая|вторая) труба(?: заполняет резервуар объемом (?P<other_amount>{VALUE}) {_LITRE})?\?",
}


def prepare_workers(kind, data):
    time = duration(data["delay"])
    target_fast = data["who"] == "первый"
    if kind == "same_worker":
        if data["faster"] == "он" and (
            not target_fast or data["comparison"] != " второго"
        ):
            raise UnsupportedCondition(
                "the first worker must be consistently identified as faster"
            )
        fast, slow = scalar(data["amount"]), scalar(data["amount"])
    else:
        fast, slow = scalar(data["fast_amount"]), scalar(data["slow_amount"])
    values = {
        "fast_amount": fast,
        "slow_amount": slow,
        "gap": scalar(data["gap"]),
        "delay": time.total,
    }
    return Question("work_worker_rates", values, {"delay": time}, target_fast)


def prepare_pipes(data):
    if (data["who"], data["comparison"], data["other"]) not in {
        ("первая", "дольше", "вторая"),
        ("вторая", "быстрее", "первая"),
    }:
        raise UnsupportedCondition(
            "the second pipe must be consistently identified as faster"
        )
    target_fast = data["who"] == "вторая"
    own, other = scalar(data["amount"]), scalar(data["other_amount"] or data["amount"])
    fast, slow = (own, other) if target_fast else (other, own)
    return Question(
        "work_pipe_rates",
        {
            "fast_amount": fast,
            "slow_amount": slow,
            "gap": scalar(data["gap"]),
            "delay": scalar(data["delay"]),
        },
        {},
        target_fast,
    )


def parse(text):
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            q = (
                prepare_pipes(match.groupdict())
                if kind == "pipes"
                else prepare_workers(kind, match.groupdict())
            )
            if any(value <= 0 for value in q.values.values()):
                raise UnsupportedCondition(
                    "positive job amounts, rates and time differences are required"
                )
            return q
    from .work_combined_questions import parse as combined

    return combined(text)
