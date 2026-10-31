"""Interest-only years followed by the existing two-payment annuity equation."""

import re

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY

UNIT = r"(?:млн|тыс\.) (?:рублей|руб\.)"
PATTERN = rf"В июле (?P<year>\d{{4}}) года планируется взять кредит на пять лет в размере (?P<capital>{_MONEY}) (?P<unit>{UNIT})(?:\.|(?<=\.)) Условия его возврата таковы: — каждый январь долг (?:будет возрастать|возрастает) на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года,? необходимо выплатить (?:одним платежом )?часть долга; — в июле (?P<first>\d{{4}}), (?P<second>\d{{4}}) и (?P<third>\d{{4}}) годах (?:долг остается равен|сумма долга остается равной) (?P<balance>{_MONEY}) (?P<balance_unit>{UNIT}); — (?:платежи|выплаты) в (?P<fourth>\d{{4}}) и (?P<fifth>\d{{4}}) годах (?:должны быть )?равны; — к июлю (?P=fifth) года долг (?:должен быть|будет) выплачен полностью\. (?P<request>Сколько млн рублей составит разница между первым и последним платежами\.|На сколько рублей последняя выплата будет больше первой\?|Найдите разницу между первым и последним платежами\.)"


def multiplier(unit):
    return 1_000_000 if unit.startswith("млн") else 1000


def parse(text):
    from .annuity_questions import Question

    m = re.fullmatch(PATTERN, text)
    if not m:
        return None
    year = int(m["year"])
    if [int(m[key]) for key in ("first", "second", "third", "fourth", "fifth")] != list(
        range(year + 1, year + 6)
    ):
        raise UnsupportedCondition(
            "interest-only and annuity dates must cover five consecutive years"
        )
    capital, rate, balance = (
        scalar(m[key].replace(" ", "")) for key in ("capital", "rate", "balance")
    )
    units = multiplier(m["unit"])
    if (
        min(capital, rate) <= 0
        or balance * multiplier(m["balance_unit"]) != capital * units
    ):
        raise UnsupportedCondition(
            "positive capital and rate and the unchanged initial principal are required"
        )
    requested = (
        1_000_000
        if m["request"].startswith("Сколько млн")
        else (1 if m["request"].startswith("На сколько рублей") else units)
    )
    return Question(
        "grace",
        capital,
        None,
        rate,
        2,
        year,
        grace=3,
        scale=sp.Rational(units, requested),
        unit="млн руб." if units == 1_000_000 else "тыс. руб.",
    )
