"""Ordered elementary outcomes of fair six-sided dice."""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import product

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

_SUM = re.compile(
    rf"В случайном эксперименте бросают (?P<n>{COUNT}) игральные кости\. Найдите вероятность того, что в сумме выпадет (?P<sum>\d+) очк(?:о|а|ов)\."
)
_COUNT = re.compile(
    r"Игральный кубик бросают дважды\. Сколько элементарных исходов опыта благоприятствуют событию (?:«)?А = (?:\\?\{)?сумма очков равна (?P<sum>\d+)(?:\\?\})?(?:»)?\?"
)
_CONDITIONAL = re.compile(
    r"Симметричную игральную кость бросили (?P<n>\d+) раз(?:а)?\. Известно, что в сумме выпало (?P<sum>\d+) очков\. Какова вероятность события «хотя бы раз выпало (?P<face>\d+) очк(?:о|а|ов)»\?"
)
_CONDITIONAL_TWO = re.compile(
    r"При двукратном бросании игральной кости в сумме выпало (?P<sum>\d+) очк(?:о|а|ов)\. Какова вероятность того, что хотя бы раз выпало (?P<face>\d+) очк(?:о|а|ов)\?"
)
_POSITION = re.compile(
    r"Игральный кубик бросают дважды\. Известно, что в сумме выпало (?P<sum>\d+) очк(?:о|а|ов)\. Найдите вероятность того, что (?:в (?P<first>первый)|во (?P<second>второй)) раз выпало (?P<face>\d+) очк(?:о|а|ов)\."
)
_EQUAL = re.compile(
    r"Игральную кость бросают два раза\. Найдите вероятность того, что выпавшие значения (?P<kind>совпадают|различны)\."
)
_EVENTS = {
    "sum": lambda row, value: sum(row) == value,
    "contains": lambda row, value: value in row,
    "first": lambda row, value: row[0] == value,
    "second": lambda row, value: row[-1] == value,
    "equal": lambda row, _value: len(set(row)) == 1,
    "different": lambda row, _value: len(set(row)) == len(row),
}


@dataclass(frozen=True)
class DiceCase:
    throws: int
    event: str
    value: int = 0
    conditional_sum: int | None = None
    count_only: bool = False
    places: int | None = None


def parse(text: str) -> DiceCase:
    text, places = rounding(normalize(text))
    if match := _SUM.fullmatch(text):
        return DiceCase(count(match["n"]), "sum", int(match["sum"]), places=places)
    if match := _COUNT.fullmatch(text):
        if places is not None:
            raise UnsupportedCondition("an elementary-outcome count is an integer")
        return DiceCase(2, "sum", int(match["sum"]), count_only=True)
    if match := _CONDITIONAL.fullmatch(text):
        return DiceCase(
            int(match["n"]),
            "contains",
            int(match["face"]),
            int(match["sum"]),
            places=places,
        )
    if match := _CONDITIONAL_TWO.fullmatch(text):
        return DiceCase(
            2, "contains", int(match["face"]), int(match["sum"]), places=places
        )
    if match := _POSITION.fullmatch(text):
        return DiceCase(
            2,
            "first" if match["first"] else "second",
            int(match["face"]),
            int(match["sum"]),
            places=places,
        )
    if match := _EQUAL.fullmatch(text):
        return DiceCase(
            2, "equal" if match["kind"] == "совпадают" else "different", places=places
        )
    raise UnsupportedCondition("unsupported complete dice experiment")


def outcomes(case: DiceCase):
    # shortcut: enumerate at most six throws; use counting formulas before supporting larger experiments.
    if not 1 <= case.throws <= 6:
        raise UnsupportedCondition("dice enumeration supports one to six throws")
    if case.event in ("contains", "first", "second") and not 1 <= case.value <= 6:
        raise UnsupportedCondition("a die face must be between one and six")
    domain = [
        row
        for row in product(range(1, 7), repeat=case.throws)
        if case.conditional_sum is None or sum(row) == case.conditional_sum
    ]
    if not domain:
        raise UnsupportedCondition("the conditioning event has no outcomes")

    predicate = _EVENTS.get(case.event)
    if predicate is None:
        raise UnsupportedCondition("unknown dice event")
    return domain, [row for row in domain if predicate(row, case.value)]


def _list(rows) -> str:
    return ", ".join("(" + "; ".join(map(str, row)) + ")" for row in rows) or "нет"


def render(case: DiceCase) -> tuple[str, str]:
    domain, favorable = outcomes(case)
    if case.count_only:
        html = (
            "<p>Перечислим упорядоченные исходы, в которых сумма очков равна "
            + str(case.value)
            + ":</p>"
        )
        html += (
            "<p>"
            + _list(favorable)
            + ".</p>"
            + line(rf"N_{{\mathrm{{благ}}}}={len(favorable)}")
        )
        return str(len(favorable)), html
    if case.conditional_sum is None:
        html = "<p>Каждый кубик может выпасть шестью способами. Порядок бросаний учитываем, поэтому все упорядоченные исходы равновозможны:</p>"
        html += line(rf"N_{{\mathrm{{общ}}}}=6^{{{case.throws}}}={len(domain)}")
    else:
        html = "<p>С учётом известной суммы оставим только допустимые упорядоченные исходы:</p>"
        if len(domain) <= 36:
            html += "<p>" + _list(domain) + ".</p>"
        html += line(rf"N_{{\mathrm{{общ}}}}={len(domain)}")
    html += "<p>Благоприятные исходы удовлетворяют событию из условия"
    if len(favorable) <= 36:
        html += ": " + _list(favorable)
    html += ".</p>" + line(rf"N_{{\mathrm{{благ}}}}={len(favorable)}")
    answer, calculation = probability(len(favorable), len(domain), case.places)
    return answer, html + calculation


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(
        context, allow_inline_latex=True
    )
    answer, html = render(parse(text))
    return finish(condition, answer_section, solution, answer, html)
