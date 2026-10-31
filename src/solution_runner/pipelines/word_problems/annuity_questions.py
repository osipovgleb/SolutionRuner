"""Complete equal-payment loans with refinancing or an interest-only prefix."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY, _NAME

TERMS = rf"Условия его возврата таковы: — каждый январь долг (?:увеличивается|возрастает) на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года необходимо выплатить одним платежом часть долга\. "
TOTAL = (
    rf"В июле(?: (?P<year>\d{{4}}) года)? планируется взять кредит в банке на сумму (?P<capital>{_MONEY}) рублей\. "
    + TERMS
    + r"Сколько рублей будет выплачено банку, если известно, что кредит будет полностью погашен (?:(?P<two>двумя) равными платежами, то есть за два года\.|(?P<three>тремя) равными платежами\(то есть за три года\)\?)"
)
SHORT = rf"Был выдан кредит на (?P<capital>{_MONEY}) рублей\. Известно, что банк каждый год увеличивает сумму кредита на (?P<rate>{VALUE}) процентов, после чего происходит платеж\. Кредит был полностью выплачен за 2 года, причем платежи были равными\. Найдите общую сумму, выплаченную клиентом банку\."
TABLE = (
    rf"В июле (?P<year>\d{{4}}) года планируется взять кредит (?P<capital>{_MONEY}) рублей в банке на три года\. "
    + TERMS
    + r"Сколько рублей составит общая сумма платежей после полного погашения кредита, если известно, что кредит будет полностью погашен тремя равными платежами\?"
)
PRINCIPAL = rf"В июле планируется взять в банке некоторую сумму в кредит на три года\. Условия его возврата таковы: — каждый январь долг возрастает на (?P<rate>{VALUE})% по сравнению с концом предыдущего года; — с февраля по июнь каждого года нужно внести платеж, равный (?P<payment>{_MONEY}) млн рублей\. Сколько рублей было взято в банке, если известно, что долг был полностью погашен тремя равными платежами\(то есть за три года\)\?"
REFINANCE = rf"В январе (?P<year>\d{{4}}) года (?P<name>{_NAME}) взял кредит в банке на сумму (?P<capital>{_MONEY}) рублей\. По договору с банком (?P=name) должен был погасить долг двумя равными платежами в феврале (?P<first>\d{{4}}) года и феврале (?P<last>\d{{4}}) года, при условии, что в январе (?P=first) года и январе (?P=last) года сумма оставшегося долга увеличивается на (?P<rate>{VALUE})%\. В феврале (?P=first) года (?P=name) сделал первую выплату в соответствии с договором\. После этого ему удалось договориться с банком о рефинансировании кредита и уменьшить процент, на который сумма долга вырастет в январе (?P=last) года, до (?P<new_rate>{VALUE})%\. (?:Сколько рублей|Какую сумму) сэкономит (?P=name) на рефинансировании своего кредита\?"


@dataclass(frozen=True)
class Question:
    style: str
    capital: sp.Rational | None
    payment: sp.Rational | None
    rate: sp.Rational
    periods: int
    year: int | None = None
    new_rate: sp.Rational | None = None
    grace: int = 0
    scale: sp.Rational | int = 1
    unit: str = "руб."


def parse(text):
    from .grace_credit import parse as parse_grace

    if grace := parse_grace(text):
        return grace
    patterns = {
        "total": TOTAL,
        "two": SHORT,
        "table": TABLE,
        "principal": PRINCIPAL,
        "refinance": REFINANCE,
    }
    matches = [
        (style, m) for style, p in patterns.items() if (m := re.fullmatch(p, text))
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "the entire equal-payment credit question must match"
        )
    style, match = matches[0]
    v = match.groupdict()
    if style == "total":
        style = "two" if v["two"] else "three"

    def money(key):
        return scalar(v[key].replace(" ", "")) if v.get(key) else None

    rate, new_rate = money("rate"), money("new_rate")
    capital, payment = money("capital"), money("payment")
    year = int(v["year"]) if v.get("year") else None
    if style == "refinance" and (
        int(v["first"]) != year + 1 or int(v["last"]) != year + 2
    ):
        raise UnsupportedCondition(
            "refinancing must affect only the second consecutive year"
        )
    if (
        rate <= 0
        or any(x is not None and x <= 0 for x in (capital, payment))
        or (new_rate is not None and not 0 <= new_rate < rate)
    ):
        raise UnsupportedCondition(
            "positive amounts and interest, and a strictly lower refinancing rate are required"
        )
    return Question(
        style,
        capital,
        payment,
        rate,
        2 if style in {"two", "refinance"} else 3,
        year,
        new_rate,
    )
