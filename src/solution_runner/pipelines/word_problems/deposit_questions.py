"""Complete annual-deposit schedules, cash-flow timing and requested money units."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .yearly_growth import _MONEY

UNIT = r"(?:тысяч|миллионов)"
OUTPUT = r"(?:рублях|тысячах рублей|миллионах рублей)"
ORDINALS = (
    "первого",
    "второго",
    "третьего",
    "четвертого",
    "пятого",
    "шестого",
    "седьмого",
    "восьмого",
    "девятого",
    "десятого",
)
ORD = "(?:" + "|".join(ORDINALS) + ")"
TERM = r"(?P<periods>\d+) (?:год|года|лет)"
FORWARD = rf"В \d{{4}} году был открыт вклад на сумму (?P<capital>{_MONEY}) (?P<unit>{UNIT}) рублей, срок — {TERM}\. В конце каждого года банк увеличивает размер вклада на (?P<rate>{VALUE})%\. Кроме того, в начале каждого года, начиная со второго, (?P<flow_kind>вклад пополняется на|со вклада снимается) (?P<flow>{_MONEY}) (?P<flow_unit>{UNIT}) рублей\. Определите сумму, которая будет (?:находится|находиться) на вкладе к концу (?P<end>{ORD}) года размещения денежных средств\. Ответ дайте в (?P<output>{OUTPUT})\."
INITIAL = rf"В \d{{4}} году был открыт вклад на {TERM} (?:на )?некоторую сумму под (?P<rate>{VALUE})% годовых\. Определите изначальную величину вклада\s*\(в (?P<output>{OUTPUT})\), если известно, что в начале (?P<flow_years>{ORD}(?:, {ORD})* и {ORD}) года вклад пополнялся на (?P<flow>{_MONEY}) (?P<flow_unit>{UNIT}) рублей, а в конце (?P<end>{ORD}) года сумма на вкладе составила (?P<final>{_MONEY}) (?P<unit>{UNIT}) рублей\."
RATE = rf"В \d{{4}} году был открыт вклад на сумму (?P<capital>{_MONEY}) (?P<unit>{UNIT}) рублей сроком на {TERM}\. В конце каждого года банк увеличивает размер вклада на r\s*%\. Известно, что в конце (?P<end>{ORD}) года сумма на вкладе составит (?P<final>{_MONEY}) (?P<final_unit>{UNIT}) рублей\. Найдите r\."
COMPARE = rf"При открытии вклада на сумму (?P<capital>{_MONEY}) (?P<unit>{UNIT}) рублей на {TERM} банк предлагает два варианта\. Первый вариант — фиксированная ставка (?P<rate>{VALUE})% годовых на весь срок\. При втором варианте ставка в первый год составляет (?P<first>{VALUE})% годовых, а каждый следующий год увеличивается на (?P<step>{VALUE})%\. Определите, при выборе какого из вариантов к концу (?P<end>{ORD}) года сумма на вкладе окажется наибольшей\. В ответе укажите разницу между суммами вкладов к концу (?P<asked_end>{ORD}) года в (?P<output>{OUTPUT})\."
SCALES = {
    "тысяч": sp.Integer(1000),
    "миллионов": sp.Integer(1000000),
    "рублях": sp.Integer(1),
    "тысячах рублей": sp.Integer(1000),
    "миллионах рублей": sp.Integer(1000000),
}


@dataclass(frozen=True)
class Question:
    kind: str
    periods: int
    unit: sp.Integer
    output_unit: sp.Integer
    capital: sp.Rational | None
    rate: sp.Rational | None
    flow: sp.Rational = sp.S.Zero
    final: sp.Rational | None = None
    first: sp.Rational | None = None
    step: sp.Rational | None = None


def parse(text):
    patterns = {
        "forward": FORWARD,
        "initial": INITIAL,
        "rate": RATE,
        "compare": COMPARE,
    }
    matches = [
        (kind, m)
        for kind, pattern in patterns.items()
        if (m := re.fullmatch(pattern, text))
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "the complete annual deposit schedule must be recognized"
        )
    kind, m = matches[0]
    v = m.groupdict()
    periods = int(v["periods"])
    if (
        not 1 <= periods <= 10
        or v["end"] != ORDINALS[periods - 1]
        or (v.get("asked_end") and v["asked_end"] != v["end"])
    ):
        raise UnsupportedCondition(
            "the term and every requested final year must agree within ten annual periods"
        )
    unit = SCALES[v["unit"]]
    numeric = lambda key: scalar(v[key].replace(" ", "")) if v.get(key) else None
    capital, rate, flow, final, first, step = (
        numeric(k) for k in ("capital", "rate", "flow", "final", "first", "step")
    )
    if any(x is not None and x <= 0 for x in (capital, flow, final)) or any(
        x is not None and x < 0 for x in (rate, first, step)
    ):
        raise UnsupportedCondition(
            "positive money amounts and nonnegative annual rates are required"
        )
    if flow is not None:
        flow = flow * SCALES[v["flow_unit"]] / unit
        if v.get("flow_kind") == "со вклада снимается":
            flow = -flow
    if kind == "initial":
        years = [ORDINALS.index(x) + 1 for x in re.split(r", | и ", v["flow_years"])]
        if years != list(range(2, periods + 1)):
            raise UnsupportedCondition(
                "the explicit cash-flow years must cover exactly years two through maturity"
            )
    if kind == "rate":
        final = final * SCALES[v["final_unit"]] / unit
    return Question(
        kind,
        periods,
        unit,
        SCALES[v["output"]] if v.get("output") else unit,
        capital,
        rate,
        flow or sp.Integer(0),
        final,
        first,
        step,
    )
