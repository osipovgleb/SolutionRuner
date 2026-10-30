"""Full adiabatic-gas statements and exact, positive power-law data."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .physical_questions import scalar

_COMPRESSION = r"Установка для демонстрации адиабатического сжатия представляет собой сосуд с поршнем, резко сжимающим газ\. При это(?:м)? объем и давление связаны соотношением "
_SINGLE = (
    _COMPRESSION
    + r"pV\^\{(?P<exponent>.+?)\}=const, где p\(атм\)[—-] давление газа, V — объем газа в литрах\. Изначально объем газа равен (?P<initial>.+?) л, а его давление равно одной атмосфере\. "
)
_PATTERNS = (
    (
        "absolute",
        re.compile(
            r"При адиабатическом процессе для идеального газа выполняется закон pV\^\{k\}=(?P<constant>.+?)\s*Па\s*\\cdot\s*м\^\{(?P<dimension>.+?)\}, где p [—-] давление газа(?: в паскалях|\(в Па\)), V [—-] объем газа(?: в кубических метрах|\(в м\^\{3\}\)), k=(?P<exponent>.+?)\. Найдите, какой объем V\(в (?:куб\. м|м\^\{3\})\)будет занимать газ при давлении p, равном (?P<pressure>.+?) Па\."
        ),
    ),
    (
        "factor",
        re.compile(
            r"Уравнение процесса, в котором участвовал газ, записывается в виде pV\^\{a\}=const, где p\(Па\)— давление газа, V — объем газа в кубических метрах, a — положительная константа\. При каком наименьшем значении константы a (?P<volume_direction>уменьшение|увеличение) (?:(?:в (?P<volume_factor>.+?) (?:раза|раз))|(?P<volume_word>вчетверо)) объема газа, участвующего в этом процессе, приводит к (?P<pressure_direction>увеличению|уменьшению) давления не менее,? чем в (?P<pressure_factor>.+?) раз(?:а)?\?"
        ),
    ),
    (
        "compression_min",
        re.compile(
            _SINGLE
            + r"В соответствии с техническими характеристиками поршень насоса выдерживает давление не более (?P<pressure>.+?) атмосфер\. Определите, до какого минимального объема можно сжать газ\. Ответ выразите в литрах\."
        ),
    ),
    (
        "compression_equal",
        re.compile(
            _SINGLE
            + r"До какого объема нужно сжать газ, чтобы давление в сосуде поднялось до (?P<pressure>.+?) атмосфер\? Ответ выразите в литрах\."
        ),
    ),
    (
        "compression_equal",
        re.compile(
            _COMPRESSION
            + r"p_1V_1\^\{(?P<exponent>.+?)\}=p_2V_2\^\{(?P<other_exponent>.+?)\}, где p_1 и p_2 — давление газа\(в атмосферах\)в начальном и конечном состояниях, V_1 и V_2 — объем газа\(в литрах\)в начальном и конечном состояниях\. Изначально объем газа равен (?P<initial>.+?) л, а давление газа равно одной атмосфере\. До какого объема нужно сжать газ, чтобы давление в сосуде стало (?P<pressure>.+?) атмосфер\? Ответ дайте в литрах\."
        ),
    ),
)


@dataclass(frozen=True)
class Question:
    kind: str
    values: dict
    source: dict


def parse(text):
    text = (
        text.replace(r"\mathrm{Па}", "Па")
        .replace(r"\,", "")
        .replace("·", r"\cdot")
        .replace("p(атм.)", "p(атм)")
    )
    for kind, pattern in _PATTERNS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        fields = {k: v for k, v in match.groupdict().items() if v is not None}
        values = {
            k: scalar("2" if v == "два" else v.replace(" ", ""))
            for k, v in fields.items()
            if k not in ["volume_direction", "pressure_direction", "volume_word"]
        }
        if fields.get("volume_word"):
            values["volume_factor"] = sp.Integer(4)
        if any(v <= 0 for v in values.values()):
            raise UnsupportedCondition("positive gas parameters are required")
        if kind == "absolute" and values["dimension"] != 3 * values["exponent"]:
            raise UnsupportedCondition(
                "the gas constant units contradict the volume exponent"
            )
        if (
            "other_exponent" in values
            and values["other_exponent"] != values["exponent"]
        ):
            raise UnsupportedCondition("both gas states must use the same exponent")
        if kind == "factor":
            if (
                values["volume_factor"] <= 1
                or values["pressure_factor"] <= 1
                or (fields["volume_direction"] == "уменьшение")
                != (fields["pressure_direction"] == "увеличению")
            ):
                raise UnsupportedCondition(
                    "positive exponents require opposite volume and pressure changes by factors greater than one"
                )
            values["compression"] = fields["volume_direction"] == "уменьшение"
        if kind.startswith("compression") and values["pressure"] < 1:
            raise UnsupportedCondition(
                "compression cannot reduce the initial one-atmosphere pressure"
            )
        return Question(kind, values, fields)
    raise UnsupportedCondition("the complete gas power-law question must be recognized")
