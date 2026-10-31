"""Read complete loans with equal initial payments or two specified payments."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY

UNIT = r"(?:тыс\. (?:рублей|руб\.)|тысяч рублей)"
HEADER = rf"В июле (?P<year>\d{{4}}) года планируется взять кредит (?:на три года(?: в размере (?P<capital>{_MONEY}) {UNIT})?|в банке в размере (?P<other_capital>{_MONEY}) {UNIT})(?:\.|(?<=\.)) Условия его возврата таковы: — каждый январь долг (?:будет возрастать|увеличивается) на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года необходимо выплатить (?:одним платеж[оа]м )?часть долга; — (?:платежи|платеж|выплаты) в (?P<first>\d{{4}}) и (?:в )?(?P<second>\d{{4}}) годах (?:(?:(?:должны|должен) быть )?(?:равны(?:ми)?|(?:по )?(?P<payment>{_MONEY}) {UNIT})); — (?:к июлю (?P<last>\d{{4}}) года долг должен быть выплачен полностью|в июле (?P<other_last>\d{{4}}) долг должен быть полностью погашен)\. (?P<tail>.+)"
KNOWN_LAST = rf"Известно, что платеж в (?P<given_year>\d{{4}}) году (?:составит|будет равен) (?P<last_payment>{_MONEY}) {UNIT}(?:\.|(?<=\.)) "
KNOWN_TOTAL = rf"Сумма всех выплат равна (?P<total>{_MONEY}) {UNIT}(?:\.|(?<=\.)) "
FIRST = r"Сколько рублей составит платеж в (?P<asked_year>\d{4}) году\?"
LAST = r"Сколько тысяч рублей составит платеж в (?P<asked_year>\d{4}) году\?"
TOTAL = r"Найдите сумму всех платежей после полного погашения кредита\.(?: Ответ дайте в рублях\.)?"
CAPITAL = r"Какую сумму(?:\(в (?:тысячах рублей|тыс\. руб\.)\))?\s*планируется взять в кредит\?(?: Ответ дайте в тысячах рублей\.)?"


@dataclass(frozen=True)
class Question:
    target: str
    year: int
    rate: sp.Rational | None
    capital: sp.Rational | None
    payment: sp.Rational | None
    last: sp.Rational | None
    total: sp.Rational | None
    scale: int


def parse(text):
    from .loan_rate import parse as parse_rate

    if rate := parse_rate(text):
        return rate
    m = re.fullmatch(HEADER, text)
    if not m:
        raise UnsupportedCondition(
            "the full three-year equal-initial-payment loan must match"
        )
    v = m.groupdict()
    year = int(v["year"])
    if (
        any(
            int(v[key]) != year + offset
            for key, offset in (("first", 1), ("second", 2))
        )
        or int(v["last"] or v["other_last"]) != year + 3
    ):
        raise UnsupportedCondition(
            "all payment dates must follow three consecutive years"
        )
    endings = {
        "first": (KNOWN_LAST + FIRST, KNOWN_TOTAL + FIRST),
        "total": (KNOWN_LAST + TOTAL, TOTAL),
        "last": (LAST,),
        "capital": (KNOWN_LAST + CAPITAL,),
    }
    matches = [
        (target, t)
        for target, ps in endings.items()
        for p in ps
        if (t := re.fullmatch(p, v["tail"]))
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "the complete requested amount and last-payment data must match"
        )
    target, t = matches[0]
    tail = t.groupdict()
    if (tail.get("given_year") and int(tail["given_year"]) != year + 3) or (
        tail.get("asked_year")
        and int(tail["asked_year"]) != year + (3 if target == "last" else 1)
    ):
        raise UnsupportedCondition(
            "the stated and requested payments must refer to their actual years"
        )

    def money(value):
        return scalar(value.replace(" ", "")) if value else None

    capital = money(v["capital"] or v["other_capital"])
    payment = money(v["payment"])
    last, total = money(tail.get("last_payment")), money(tail.get("total"))
    rate = money(v["rate"])
    if rate <= 0 or any(
        x is not None and x <= 0 for x in (capital, payment, last, total)
    ):
        raise UnsupportedCondition(
            "positive loan amounts, payments and interest are required"
        )
    if (
        (target == "capital") != (capital is None)
        or (target in {"capital", "last"} and payment is None)
        or (target == "first" and payment is not None)
        or (target == "total" and (payment is None) == (last is None))
    ):
        raise UnsupportedCondition(
            "the known principal and payments must uniquely determine the requested amount"
        )
    # Adjacent children omit units; retain their parent's ruble-total or thousand-total convention.
    scale = (
        1000
        if target == "first"
        or (
            target == "total"
            and (payment is not None or v["tail"].endswith("Ответ дайте в рублях."))
        )
        else 1
    )
    return Question(target, year, rate, capital, payment, last, total, scale)
