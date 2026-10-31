"""Read complete equal-principal credit conditions and their exact requested bound."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY

PREFIX = rf"В июле планируется взять кредит в банке на сумму (?P<capital>{_MONEY}) млн рублей "
UNKNOWN = (
    PREFIX
    + rf"на некоторый срок\(целое число лет\)\. Условия его возврата таковы: — каждый январь долг возрастает на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года необходимо выплатить часть долга; — в июле каждого года долг должен быть на одну и ту же (?:сумму|величину) меньше долга на июль предыдущего года\. "
)
MAXIMUM = (
    UNKNOWN
    + rf"Чему будет равна общая сумма выплат(?:\(в миллионах рублей\))?\s*после полного погашения кредита, если наибольший годовой платеж составит (?P<target>{_MONEY}) млн рублей\?"
)
TERM = (
    UNKNOWN
    + rf"На сколько лет (?:был взят|планируется взять) кредит, если(?: известно, что)? общая сумма выплат после (?:полного погашения кредита|его полного погашения|его погашения) (?:составила|составит|равнялась) (?P<target>{_MONEY}) млн рублей\?"
)
RATE = (
    PREFIX
    + rf"на срок (?P<periods>\d+) лет\. Условия возврата таковы: — каждый январь долг возрастает на r\s*% по сравнению с концом предыдущего года; — с февраля по июнь необходимо выплатить часть долга так, чтобы на начало июля каждого года долг уменьшался на одну и ту же сумму по сравнению с предыдущим июлем\. Найдите наименьшую возможную ставку r, если известно, что последний платеж будет не менее (?P<target>{_MONEY}) млн рублей\."
)


@dataclass(frozen=True)
class Question:
    kind: str
    capital: sp.Rational
    target: sp.Rational
    rate: sp.Rational | None
    periods: int | None


def parse(text):
    patterns = {"maximum": MAXIMUM, "term": TERM, "rate_bound": RATE}
    matches = [
        (kind, m)
        for kind, pattern in patterns.items()
        if (m := re.fullmatch(pattern, text))
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "the entire differentiated credit question must match"
        )
    kind, m = matches[0]
    v = m.groupdict()
    capital, target = (scalar(v[k].replace(" ", "")) for k in ("capital", "target"))
    rate = scalar(v["rate"]) if v.get("rate") else None
    periods = int(v["periods"]) if v.get("periods") else None
    if (
        min(capital, target) <= 0
        or (rate is not None and rate <= 0)
        or (periods is not None and not 1 <= periods <= 1000)
    ):
        raise UnsupportedCondition(
            "positive principal, payment bound, interest and a bounded positive term are required"
        )
    return Question(kind, capital, target, rate, periods)
