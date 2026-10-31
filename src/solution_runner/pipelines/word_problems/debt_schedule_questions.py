"""Exact debt fractions and integer constraints, with dates and units checked."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY

UNIT = r"(?:млн (?:рублей|руб\.)|тысяч рублей|тыс\. рублей)"
ANNUAL = rf"В июле (?P<year>\d{{4}}) года планируется взять кредит в банке на (?P<periods>три|четыре) года в размере S (?P<unit>{UNIT}), где S — целое число\. Условия его возврата таковы: [—-] каждый январь долг увеличивается на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; [—-] с февраля по июнь каждого года необходимо выплатить (?:одним платежом )?часть долга; [—-] (?:в )?июле каждого года долг должен составлять часть кредита в соответствии со следующей таблицей[.:]? ТАБЛИЦА Найдите (?P<extreme>наибольшее|наименьшее)(?: значение)? S, при котором (?P<scope>каждая из выплат|общая сумма выплат) будет (?P<bound>не больше|не меньше|меньше|больше) (?P<limit>{_MONEY}) (?P<limit_unit>{UNIT})\.?"
MONTHLY = rf"15-го января был выдан полугодовой кредит на развитие бизнеса\. В таблице представлен график его погашения\. ТАБЛИЦА В конце каждого месяца, начиная с января, текущий долг увеличивался на (?P<rate>{VALUE})%, а выплаты по погашению кредита происходили в первой половине каждого месяца, начиная с февраля\. На сколько процентов общая сумма выплат при таких условиях больше суммы самого кредита\?"
GEOMETRIC = rf"В июле (?P<year>\d{{4}}) года планируется взять кредит в банке в размере S (?P<unit>тысяч рублей|тыс\. рублей) на (?P<periods>три|четыре) года\. Условия его возврата таковы: — каждый январь долг увеличивается на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года необходимо выплатить часть долга; — в июле (?P<years>\d{{4}}(?:, \d{{4}})* и \d{{4}}) годов долг должен быть на (?P<decrease>{VALUE})% меньше долга на июль предыдущего года; — к июлю (?P<last>\d{{4}}) года долг должен быть выплачен полностью\. Известно, что (?:(?:общая сумма выплат)|(?:сумма всех платежей)) по кредиту составила (?P<total>{_MONEY}) (?:тысяч рублей|тыс\. рублей)\. Найдите S\."


@dataclass(frozen=True)
class Question:
    kind: str
    year: int
    rate: sp.Rational
    ratios: tuple
    unit: str
    scope: str = ""
    bound: str = ""
    extreme: str = ""
    limit: sp.Rational | None = None


def unit(text):
    return "млн руб." if text.startswith("млн") else "тыс. руб."


def ratios_from_table(tables, year, periods, units):
    if (
        len(tables) != 1
        or len(tables[0]) != 2
        or any(len(row) != periods + 2 for row in tables[0])
    ):
        raise UnsupportedCondition(
            "exactly two rectangular debt rows must cover the complete term"
        )
    dates, debts = tables[0]
    if dates != ["Месяц и год"] + [
        "Июль " + str(year + j) for j in range(periods + 1)
    ] or debts[0] not in (
        {"Долг (в млн рублей)", "Долг (в млн руб.)"}
        if units == "млн руб."
        else {"Долг (в тыс. рублей)"}
    ):
        raise UnsupportedCondition(
            "debt table dates and monetary units must match the condition"
        )
    if debts[1] != "S" or debts[-1] != "0":
        raise UnsupportedCondition("the debt schedule must start at S and end at zero")
    ratios = [sp.Integer(1)]
    for cell in debts[2:-1]:
        m = re.fullmatch(rf"({VALUE})\s*S", cell)
        if not m:
            raise UnsupportedCondition(
                "each interior debt must be a numeric multiple of S"
            )
        ratios.append(scalar(m[1]))
    return tuple(ratios + [sp.Integer(0)])


def parse(text, tables):
    if m := re.fullmatch(ANNUAL, text):
        v = m.groupdict()
        year = int(v["year"])
        periods = {"три": 3, "четыре": 4}[v["periods"]]
        units = unit(v["unit"])
        if unit(v["limit_unit"]) != units or (v["extreme"] == "наибольшее") != (
            v["bound"] in {"меньше", "не больше"}
        ):
            raise UnsupportedCondition(
                "the extremum direction and bound units must agree"
            )
        ratios = ratios_from_table(tables, year, periods, units)
        q = Question(
            "bound",
            year,
            scalar(v["rate"]),
            ratios,
            units,
            v["scope"],
            v["bound"],
            v["extreme"],
            scalar(v["limit"].replace(" ", "")),
        )
    elif m := re.fullmatch(MONTHLY, text):
        if (
            len(tables) != 1
            or len(tables[0]) != 2
            or tables[0][0] != ["Дата"] + ["15." + str(i).zfill(2) for i in range(1, 8)]
            or len(tables[0][1]) != 8
            or tables[0][1][0] != "Долг (в процентах от кредита)"
        ):
            raise UnsupportedCondition(
                "the half-year debt table must cover January through July"
            )
        ratios = []
        for cell in tables[0][1][1:]:
            cell_match = re.fullmatch(rf"({VALUE})%", cell)
            if not cell_match:
                raise UnsupportedCondition(
                    "every monthly debt must be an explicit percentage"
                )
            ratios.append(scalar(cell_match[1]) / 100)
        q = Question("monthly", 0, scalar(m["rate"]), tuple(ratios), "руб.")
    elif m := re.fullmatch(GEOMETRIC, text):
        year = int(m["year"])
        periods = {"три": 3, "четыре": 4}[m["periods"]]
        years = [int(x) for x in re.findall(r"\d{4}", m["years"])]
        decrease = scalar(m["decrease"])
        if (
            tables
            or years != list(range(year + 1, year + periods))
            or int(m["last"]) != year + periods
            or not 0 < decrease < 100
        ):
            raise UnsupportedCondition(
                "the geometric debt reductions must cover all intermediate consecutive years"
            )
        ratios = tuple((1 - decrease / 100) ** j for j in range(periods)) + (
            sp.Integer(0),
        )
        q = Question(
            "geometric",
            year,
            scalar(m["rate"]),
            ratios,
            "тыс. руб.",
            limit=scalar(m["total"].replace(" ", "")),
        )
    else:
        raise UnsupportedCondition(
            "the entire prescribed debt schedule question must match"
        )
    if (
        q.rate <= 0
        or (q.limit is not None and q.limit <= 0)
        or q.ratios[0] != 1
        or q.ratios[-1] != 0
        or any(not 0 <= b < a <= 1 for a, b in zip(q.ratios, q.ratios[1:]))
    ):
        raise UnsupportedCondition(
            "positive interest and strictly decreasing debt fractions from one to zero are required"
        )
    return q
