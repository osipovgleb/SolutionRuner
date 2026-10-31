"""Complete arithmetic-series questions with explicit requested day and units."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition
from .group_99570 import _dative

_NAME = r"[А-ЯЁ][а-яё]+"
_DAYS = r"д(?:ень|ня|ней)"
_TASKS = r"задач(?:а|и)?"
_CARDS = r"открыт(?:ка|ки|ок)"
_ORDINALS = {
    "первый": 1,
    "второй": 2,
    "третий": 3,
    "четвертый": 4,
    "пятый": 5,
    "шестой": 6,
    "седьмой": 7,
    "восьмой": 8,
    "девятый": 9,
    "десятый": 10,
}
_DAY = "(?:" + "|".join(_ORDINALS) + ")"
PATTERNS = {
    "fence": rf"Бригада маляров красит забор длиной (?P<total>{VALUE}) метров, ежедневно увеличивая норму покраски на одно и то же число метров\. Известно, что за первый и последний день в сумме бригада покрасила (?P<end_sum>{VALUE}) метров забора\. Определите, сколько дней бригада маляров красила весь забор\.",
    "snail": rf"Улитка ползет от одного дерева до другого\. Каждый день она проползает на одно и то же расстояние больше, чем в предыдущий день\. Известно, что за первый и последний дни улитка проползла в общей сложности (?P<end_sum>{VALUE}) метров\. Определите, сколько дней улитка потратила на весь путь, если расстояние между деревьями равно (?P<total>{VALUE}) метрам\.",
    "tunnel": rf"Рабочие прокладывают тоннель длиной (?P<total>{VALUE}) метров, ежедневно увеличивая норму прокладки на одно и то же число метров\. Известно, что за первый день рабочие проложили (?P<first>{VALUE}) метр(?:а|ов)? т[оу]ннеля\. Определите, сколько метров т[оу]ннеля проложили рабочие в последний день, если вся работа была выполнена за (?P<days>{VALUE}) {_DAYS}\.",
    "tasks": rf"(?P<who>{_NAME}) надо решить (?P<total>{VALUE}) {_TASKS}\. Ежедневно он решает на одно и то же количество задач больше по сравнению с предыдущим днем\. Известно, что за первый день (?P<name>{_NAME}) решил (?P<first>{VALUE}) {_TASKS}\. Определите, сколько задач решил (?P=name) в последний день, если со всеми задачами он справился за (?P<days>{VALUE}) {_DAYS}\.",
    "tourist": rf"Турист идет из одного города в другой, каждый день проходя больше, чем в предыдущий день, на одно и то же расстояние\. Известно, что за первый день турист прошел (?P<first>{VALUE}) километров\. Определите, сколько километров прошел турист за (?P<asked>{_DAY}) день, если весь путь он прошел за (?P<days>{VALUE}) {_DAYS}, а расстояние между городами составляет (?P<total>{VALUE}) километров\.",
    "truck": rf"Грузовик перевозит партию щебня массой (?P<total>{VALUE}) тонн(?:ы)?, ежедневно увеличивая норму перевозки на одно и то же число тонн\. Известно, что за первый день было перевезено (?P<first>{VALUE}) тонн(?:ы|а)? щебня\. Определите, сколько тонн щебня было перевезено за (?P<asked>{_DAY}) день, если вся работа была выполнена за (?P<days>{VALUE}) {_DAYS}\.",
    "cards": rf"(?P<who>{_NAME}) надо подписать (?P<total>{VALUE}) {_CARDS}\. Ежедневно она подписывает на одно и то же количество открыток больше по сравнению с предыдущим днем\. Известно, что за первый день (?P<name>{_NAME}) подписала (?P<first>{VALUE}) {_CARDS}\. Определите, сколько открыток было подписано за (?P<asked>{_DAY}) день, если вся работа была выполнена за (?P<days>{VALUE}) {_DAYS}\.",
}


@dataclass(frozen=True)
class Question:
    kind: str
    values: dict
    name: str = ""

    @property
    def counted(self):
        return self.kind in {"tasks", "cards"}


def parse(text):
    for kind, pattern in PATTERNS.items():
        match = re.fullmatch(pattern, text.replace("ё", "е"))
        if not match:
            continue
        data = match.groupdict()
        name = text[match.start("name") : match.end("name")] if "name" in data else ""
        if name and _dative(name).replace("ё", "е") != data["who"]:
            raise UnsupportedCondition(
                "the named participant must agree in every part of the question"
            )
        values = {
            k: scalar(data[k])
            for k in ("total", "end_sum", "first", "days")
            if k in data
        }
        if any(v <= 0 for v in values.values()):
            raise UnsupportedCondition(
                "positive daily amounts, sums and day counts are required"
            )
        if "days" in values:
            values["asked"] = (
                sp.Integer(_ORDINALS[data["asked"]])
                if "asked" in data
                else values["days"]
            )
        return Question(kind, values, name)
    raise UnsupportedCondition(
        "the complete arithmetic-progression question must be recognized"
    )
