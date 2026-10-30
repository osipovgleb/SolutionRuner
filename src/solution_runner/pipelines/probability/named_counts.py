"""Uniform choice from explicitly listed people or sweets."""

import re
from html import escape

from .common import COUNT, UnsupportedCondition, count, line

_CANDIES = re.compile(
    rf"В кармане у [А-Я][а-я]+ было (?P<n>{COUNT}) конфет(?:а|ы)? — (?P<items>«[^«»]+»(?:(?:, | и )«[^«»]+»)*)\, а также ключи от квартиры\. Вынимая ключи, [А-Я][а-я]+ случайно выронил из кармана одну конфету\. Найдите вероятность того, что потерялась конфета «(?P<target>[^«»]+)»\."
)
_LOTTERY = re.compile(
    r"(?P<names>[А-Я][а-я]+(?:(?:, | и )[А-Я][а-я]+)+) бросили жребий — кому начинать игру\. Найдите вероятность того, что начинать игру долж(?:ен|на) будет (?P<target>(?:не )?[А-Я][а-я]+|девочка|мальчик)\."
)
_FEMALE = {
    "Даша",
    "Оля",
    "Аня",
    "Нина",
    "Маша",
    "Диана",
    "Марина",
    "Катя",
    "Лена",
    "Юля",
    "Вера",
    "Ира",
    "Таня",
    "Наташа",
    "Алина",
    "Оксана",
}
_MALE = {
    "Дима",
    "Денис",
    "Вася",
    "Петя",
    "Коля",
    "Леша",
    "Тимур",
    "Костя",
    "Антон",
    "Вова",
    "Миша",
    "Артур",
    "Ваня",
    "Сеня",
    "Андрей",
    "Сергей",
    "Олег",
    "Вадим",
}


def parse(text):
    if match := _CANDIES.fullmatch(text):
        labels = re.findall(r"«([^«»]+)»", match["items"])
        total = count(match["n"])
        if total != len(labels) or match["target"] not in labels:
            raise UnsupportedCondition(
                "the candy list disagrees with the stated count or selected candy"
            )
        favorable = labels.count(match["target"])
        html = (
            "<p>Ключи не являются конфетами и в число исходов не входят. Перечислены "
            + str(total)
            + " конфет; нужная конфета — «"
            + escape(match["target"])
            + "».</p>"
        )
        return (
            total,
            favorable,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={total}")
            + line(rf"N_{{\mathrm{{благ}}}}={favorable}"),
            "P",
        )
    if match := _LOTTERY.fullmatch(text):
        names = re.split(r", | и ", match["names"])
        if len(set(names)) != len(names):
            raise UnsupportedCondition(
                "the person list must identify distinct participants"
            )
        target = match["target"]
        if target in ("девочка", "мальчик"):
            if not set(names) <= _FEMALE | _MALE:
                raise UnsupportedCondition(
                    "the requested gender is not determined by the audited name list"
                )
            selected = [
                name
                for name in names
                if name in (_FEMALE if target == "девочка" else _MALE)
            ]
        else:
            negative = target.startswith("не ")
            name = target.removeprefix("не ")
            if name not in names:
                raise UnsupportedCondition("the named participant is not in the draw")
            selected = [
                other
                for other in names
                if (other != name if negative else other == name)
            ]
        html = (
            "<p>Жребий начать игру с одинаковой вероятностью может выпасть каждому участнику. Условию подходят: "
            + (", ".join(map(escape, selected)) or "нет участников")
            + ".</p>"
        )
        return (
            len(names),
            len(selected),
            html
            + line(rf"N_{{\mathrm{{общ}}}}={len(names)}")
            + line(rf"N_{{\mathrm{{благ}}}}={len(selected)}"),
            "P",
        )
    return None
