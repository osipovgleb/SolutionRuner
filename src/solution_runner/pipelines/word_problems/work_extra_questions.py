"""Complete pair-rate, crew, planned-production and integral-task conditions."""

import re

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from ..probability.common import count
from .common import UnsupportedCondition
from .motion_questions import DURATION, Question, duration

_NAME = r"[А-Я][а-я]+"
_COUNT = rf"(?:{VALUE}|одну|один|две|два|три|четыре)"
_DAYS = r"д(?:ень|ня|ней)"
_CREWS = rf"Две бригады, состоящие из рабочих одинаковой квалификации, одновременно начали (?P<task>выполнять два одинаковых заказа|строить два одинаковых дома)\. В первой бригаде было (?P<first>{VALUE}) рабочих, а во второй — (?P<second>{VALUE}) рабочих\. Через (?P<initial>{VALUE}) {_DAYS} после начала работы в первую бригаду перешли (?P<transfer>{VALUE}) рабочих из второй бригады"
PATTERNS = {
    "work_pairs_boys": rf"(?P<first>{_NAME}) и (?P<second>{_NAME}) красят забор за (?P<t12>{DURATION})\. (?P<second_again>{_NAME}) и (?P<third>{_NAME}) красят этот же забор за (?P<t23>{DURATION}), а (?P<third_again>{_NAME}) и (?P<first_again>{_NAME}) — за (?P<t13>{DURATION})\. За сколько часов мальчики покрасят забор, работая втроем\?",
    "work_pairs_pumps": rf"Первый и второй насосы наполняют бассейн за (?P<t12>{DURATION}), второй и третий — за (?P<t23>{DURATION}), а первый и третий — за (?P<t13>{DURATION})\. За сколько минут (?:эти три|три эти) насоса заполнят бассейн, работая вместе\?",
    "work_test_count": rf"(?P<first>{_NAME}) и (?P<second>{_NAME}) выполняют одинаковый тест\. (?P<first_again>{_NAME}) отвечает за час на (?P<rate1>{VALUE}) вопросов (?:теста|текста), а (?P<second_again>{_NAME}) — на (?P<rate2>{VALUE})\. Они одновременно начали отвечать на вопросы теста, и (?P<first_finish>{_NAME}) закончил свой тест позже (?P<second_genitive>{_NAME}) на (?P<delay>{DURATION})\. Сколько вопросов содержит тест\?",
    "work_tile": rf"Плиточник планирует уложить (?P<amount>{VALUE}) м\^\{{2\}} плитки\. Если он будет укладывать на (?P<gap>{VALUE}) м\^\{{2\}} в день больше, чем запланировал, то закончит работу на (?P<delay>{VALUE}) {_DAYS} раньше(?:, чем наметил)?\. Сколько квадратных метров плитки в день планирует укладывать плиточник\?",
    "crew_total": _CREWS
    + r"\. В итоге оба заказа были выполнены одновременно\. Найдите, сколько дней потребовалось на выполнение заказов\.",
    "crew_remaining": _CREWS
    + r", в результате чего оба дома были построены одновременно\. Сколько дней потребовалось бригадам, чтобы закончить работу в новом составе\?",
    "work_integer_solver": rf"(?P<fast>{_NAME}) и (?P<slow>{_NAME}) решают задачи\. За час (?P<fast_again>{_NAME}) может решить на (?P<gap>{_COUNT}) задач(?:у|и)? больше, чем (?P<slow_again>{_NAME})\(при этом оба за час решают целое количество задач\)\. Известно, что вместе они решат (?P<joint_tasks>{VALUE}) задач(?:у|и)? на (?P<delay>{DURATION}) быстрее, чем это сделал бы один (?P<fast_solo>{_NAME})\. За какое время (?P<slow_asked>{_NAME}) может решить (?P<target>{VALUE}) задач(?:у|и)?\? Ответ дайте в часах\.",
}


def genitive(name):
    if name.endswith("я"):
        return name[:-1] + "и"
    if name.endswith("а"):
        return name[:-1] + ("и" if name[-2] in "гкхжчшщ" else "ы")
    raise UnsupportedCondition(
        "an audited unambiguous genitive form of the name is required"
    )


def validate_names(kind, data):
    if kind == "work_pairs_boys":
        names = tuple(data[key] for key in ("first", "second", "third"))
        valid = len(set(names)) == 3 and all(
            data[key + "_again"] == data[key] for key in ("first", "second", "third")
        )
    elif kind == "work_test_count":
        names = (data["first"], data["second"])
        valid = (
            names[0] != names[1]
            and data["first_again"] == data["first_finish"] == names[0]
            and data["second_again"] == names[1]
            and data["second_genitive"] == genitive(names[1])
        )
    elif kind == "work_integer_solver":
        names = (data["fast"], data["slow"])
        valid = (
            names[0] != names[1]
            and data["fast_again"] == data["fast_solo"] == names[0]
            and data["slow_again"] == data["slow_asked"] == names[1]
        )
    else:
        return ()
    if not valid:
        raise UnsupportedCondition(
            "the named participants and requested roles must be consistent"
        )
    return names


def prepare(kind, data):
    if kind.startswith("crew_"):
        total = kind == "crew_total"
        expected = (
            "выполнять два одинаковых заказа"
            if total
            else "строить два одинаковых дома"
        )
        if data["task"] != expected:
            raise UnsupportedCondition(
                "the crew task and requested period must be consistent"
            )
        values = {
            key: scalar(data[key]) for key in ("first", "second", "initial", "transfer")
        }
        if any(v <= 0 for v in values.values()):
            raise UnsupportedCondition(
                "positive work times and quantities are required"
            )
        values["include_initial"] = sp.Integer(total)
        return Question("work_crews", values, {})
    time_keys = (
        ("t12", "t23", "t13")
        if kind.startswith("work_pairs_")
        else ("delay",)
        if kind in {"work_test_count", "work_integer_solver"}
        else ()
    )
    times = {key: duration(data[key]) for key in time_keys}
    scale = 60 if kind == "work_pairs_pumps" else 1
    values = {key: time.total * scale for key, time in times.items()}
    numeric = {
        "work_tile": ("amount", "gap", "delay"),
        "work_test_count": ("rate1", "rate2"),
        "work_integer_solver": ("gap", "joint_tasks", "target"),
    }.get(kind, ())
    values.update(
        (
            key,
            scalar(data[key])
            if re.fullmatch(VALUE, data[key])
            else sp.Integer(count(data[key])),
        )
        for key in numeric
    )
    if any(value <= 0 for value in values.values()):
        raise UnsupportedCondition("positive work times and quantities are required")
    names = validate_names(kind, data)
    if names:
        values["names"] = names
    return Question(kind, values, times)


def parse(text):
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text)
        if match:
            return prepare(kind, match.groupdict())
    raise UnsupportedCondition("the complete work-rate question must be recognized")
