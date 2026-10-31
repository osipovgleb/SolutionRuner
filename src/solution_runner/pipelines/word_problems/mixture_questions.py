"""Complete conservation statements, including units and counterfactual inputs."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition

_END = r"Сколько процентов составляет концентрация получившегося раствора\?"
_UNIT = r"(?:кг|литр(?:а|ов|ами)?)"
_PCT = r"(?:-процентного|%-го)"
PATTERNS = (
    (
        "dilution",
        re.compile(
            rf"В сосуд, содержащий (?P<a1>{VALUE}) (?P<unit1>{_UNIT}) (?P<p1>{VALUE})-процентного водного раствора некоторого вещества, добавили (?P<a2>{VALUE}) (?P<unit2>{_UNIT}) воды\. "
            + _END
        ),
    ),
    (
        "equal",
        re.compile(
            rf"Смешали некоторое количество (?P<p1>{VALUE}){_PCT} раствора некоторого вещества с таким же количеством (?P<p2>{VALUE}){_PCT} раствора этого вещества\. "
            + _END
        ),
    ),
    (
        "weighted",
        re.compile(
            rf"Смешали (?P<a1>{VALUE}) (?P<unit1>{_UNIT}) (?P<p1>{VALUE})-процентного водного раствора некоторого вещества с (?P<a2>{VALUE}) (?P<unit2>{_UNIT}) (?P<p2>{VALUE})-процентного водного раствора этого же вещества\. "
            + _END
            + r"(?: Конечно, вместо литров следовало бы говорить о килограммах растворов\.)?"
        ),
    ),
    (
        "drying",
        re.compile(
            rf"Изюм получается в процессе сушки винограда\. Сколько килограммов винограда потребуется для получения (?P<final_mass>{VALUE}) килограммов изюма, если виноград содержит (?P<grape_water>{VALUE})% воды, а изюм содержит (?P<raisin_water>{VALUE})% воды\?"
        ),
    ),
    (
        "alloy_total",
        re.compile(
            rf"Имеется два сплава\. Первый содержит (?P<p1>{VALUE})% никеля, второй — (?P<p2>{VALUE})% никеля\. Из этих двух сплавов получили третий сплав массой (?P<total>{VALUE}) кг, содержащий (?P<target>{VALUE})% никеля\. На сколько килограммов масса первого сплава была меньше массы второго\?"
        ),
    ),
    (
        "alloy_difference",
        re.compile(
            rf"Имеется два сплава\. Первый сплав содержит (?P<p1>{VALUE})% меди, второй — (?P<p2>{VALUE})% меди\. Масса второго сплава больше массы первого на (?P<difference>{VALUE}) кг\. Из этих двух сплавов получили третий сплав, содержащий (?P<target>{VALUE})% меди\. Найдите массу третьего сплава\. Ответ дайте в килограммах\."
        ),
    ),
    (
        "two_scenarios",
        re.compile(
            rf"Смешав (?P<p1>{VALUE})-процентный и (?P<p2>{VALUE})-процентный растворы кислоты и добавив (?P<water>{VALUE}) кг чистой воды, получили (?P<target>{VALUE})-процентный раствор кислоты\. Если бы вместо (?P<replaced>{VALUE}) кг воды добавили (?P<added>{VALUE}) кг (?P<alternative>{VALUE})-процентного раствора той же кислоты, то получили бы (?P<second_target>{VALUE})-процентный раствор кислоты\. Сколько килограммов (?P<asked>{VALUE})-процентного раствора использовали для получения смеси\?"
        ),
    ),
    (
        "unknown_concentrations",
        re.compile(
            rf"Име(?:ется|ются) два сосуда\. Первый содержит (?P<a1>{VALUE}) кг, а второй — (?P<a2>{VALUE}) кг раствора кислоты различной концентрации\. Если эти растворы смешать, то получится раствор, содержащий (?P<target>{VALUE})% кислоты\. Если же смешать равные массы этих растворов, то получится раствор, содержащий (?P<mean>{VALUE})% кислоты\. Сколько килограммов кислоты содержится в первом сосуде\?"
        ),
    ),
    (
        "acid_difference",
        re.compile(
            rf"После смешения двух растворов, первый из которых содержал (?P<acid1>{VALUE}) г кислоты, а второй содержал (?P<acid2>{VALUE}) г такой же кислоты, получили (?P<total>{VALUE}) г нового раствора\. Найдите концентрацию первого раствора\(в процентах\), если известно, что она на (?P<difference>{VALUE}) больше концентрации второго\(в процентах\)\."
        ),
    ),
    (
        "ratio",
        re.compile(
            rf"Смешали равные массы двух растворов кислоты, концентрации которых относятся как (?P<r1>{VALUE})\s*:\s*(?P<r2>{VALUE}), и получили новый раствор, содержащий (?P<target>{VALUE})% кислоты\. Найдите разность концентраций второго и первого растворов\.(?: Ответ дайте в процентах\.)?"
        ),
    ),
)
_PERCENTAGES = {
    "p1",
    "p2",
    "target",
    "alternative",
    "second_target",
    "mean",
    "grape_water",
    "raisin_water",
}


@dataclass(frozen=True)
class Question:
    kind: str
    values: dict[str, sp.Rational]
    unit: str = "кг"


def parse(text):
    text = text.replace(r"\%", "%").replace("\u2060", "").replace("‑", "-")
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        values = {
            key: scalar(value)
            for key, value in match.groupdict().items()
            if not key.startswith("unit")
        }
        if any(
            not 0 <= value <= 100
            for key, value in values.items()
            if key in _PERCENTAGES
        ):
            raise UnsupportedCondition(
                "concentrations must lie between zero and one hundred percent"
            )
        unit = "кг"
        if "unit1" in match.groupdict():
            units = [
                "л" if match[key].startswith("литр") else "кг"
                for key in ["unit1", "unit2"]
            ]
            if units[0] != units[1]:
                raise UnsupportedCondition(
                    "both mixture amounts must have the same physical unit"
                )
            unit = units[0]
        if kind == "dilution":
            values["p2"] = sp.Integer(0)
        elif kind == "equal":
            values.update(a1=sp.Integer(1), a2=sp.Integer(1))
        elif kind == "two_scenarios" and (
            values["water"] != values["replaced"] or values["asked"] != values["p1"]
        ):
            raise UnsupportedCondition(
                "the counterfactual and requested solution must match the original amounts and concentration"
            )
        return Question(kind, values, unit)
    raise UnsupportedCondition(
        "the complete conservation-of-substance question must be recognized"
    )
