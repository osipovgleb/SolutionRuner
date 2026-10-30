"""Uniform occupied slots, flight places, selected tourists and group cards."""

from __future__ import annotations

import re
from collections import Counter

from .common import COUNT, UnsupportedCondition, count, line
from .positions import ORDINAL, rank

_HELICOPTER = re.compile(
    rf"В группе туристов (?P<n>\d+) человек(?:а)?\. Их вертолетом в несколько приемов забрасывают в труднодоступный район по (?P<size>\d+) человек(?:а)? за рейс\. Порядок, в котором вертолет перевозит туристов, случаен\. Найдите вероятность того, что турист [А-Я]\. полетит (?P<rank>{ORDINAL}) рейсом вертолета\."
)
_SHOP = re.compile(
    rf"В группе туристов (?P<n>\d+) человек(?:а)?\. С помощью жребия они выбирают (?P<k>{COUNT}) человек, которые должны идти в село в магазин за продуктами\. Какова вероятность того, что турист [А-Я]\., входящий в состав группы, пойдет в магазин\?"
)
_CARDS = re.compile(
    rf"В чемпионате мира (?:участвуют|учавствуют) (?P<n>\d+) команд\. С помощью жребия их нужно разделить на (?P<groups>{COUNT}) групп(?:ы)? по (?P<size>{COUNT}) команд(?:ы)? в каждой\. В ящике вперемешку лежат карточки с номерами групп: (?P<cards>\d+(?:, \d+)*)\. Капитаны команд тянут по одной карточке\. Какова вероятность того, что команда [А-Я][А-Яа-я ]+ окажется (?:в|во) (?P<rank>{ORDINAL}) группе\?"
)
_LEAGUE = re.compile(
    rf"Проводится жеребьевка Лиги Чемпионов\. На первом этапе жеребьевки (?P<n>{COUNT}) команд, среди которых команда «(?P<a>[^«»]+)», распределились случайным образом по (?P<groups>[а-я]+) игровым группам — по одной команде в группу\. Затем по этим же группам случайным образом распределяются еще (?P<other>{COUNT}) команд, среди которых команда «(?P<b>[^«»]+)»\. Найдите вероятность того, что команды «(?P=a)» и «(?P=b)» окажутся в одной игровой группе\."
)
_CARDINAL_CASES = {
    "двум": 2,
    "трем": 3,
    "четырем": 4,
    "пяти": 5,
    "шести": 6,
    "семи": 7,
    "восьми": 8,
    "девяти": 9,
    "десяти": 10,
}


def parse(text):
    if match := _HELICOPTER.fullmatch(text):
        n, size = int(match["n"]), int(match["size"])
        if n <= 0 or size <= 0:
            raise UnsupportedCondition("flight counts must be positive")
        flights = (n + size - 1) // size
        position = rank(match["rank"], flights)
        seats = min(size, n - (position - 1) * size)
        html = "<p>Порядок перевозки случаен: турист может занять любое из мест в общей очереди. Найдём число мест на указанном рейсе:</p>"
        html += line(rf"N_{{\mathrm{{общ}}}}={n}") + line(
            rf"N_{{\mathrm{{благ}}}}={seats}"
        )
        return n, seats, html, "P"
    if match := _SHOP.fullmatch(text):
        n, k = int(match["n"]), count(match["k"])
        html = "<p>Каждый турист с одинаковой вероятностью может попасть в выбранную группу. Из общего количества выбирают указанное число человек:</p>"
        return (
            n,
            k,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={k}"),
            "P",
        )
    if match := _CARDS.fullmatch(text):
        n, groups, size = int(match["n"]), count(match["groups"]), count(match["size"])
        labels = [int(value) for value in match["cards"].split(", ")]
        if (
            groups < 1
            or size < 1
            or n != groups * size
            or len(labels) != n
            or Counter(labels) != Counter({i: size for i in range(1, groups + 1)})
        ):
            raise UnsupportedCondition(
                "group cards disagree with the declared equal groups"
            )
        target = rank(match["rank"], groups)
        favorable = labels.count(target)
        html = "<p>Каждая карточка равновозможна. Посчитаем все карточки и карточки с номером нужной группы:</p>"
        return (
            n,
            favorable,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={favorable}"),
            "P",
        )
    if match := _LEAGUE.fullmatch(text):
        n, other = count(match["n"]), count(match["other"])
        groups = _CARDINAL_CASES.get(match["groups"])
        if n < 1 or other != n or groups != n or match["a"] == match["b"]:
            raise UnsupportedCondition(
                "league draw does not place one team per equal group"
            )
        html = "<p>После первого этапа первая команда находится в одной определённой группе. На втором этапе для второй команды равновозможны все группы, а подходит ровно одна:</p>"
        return (
            n,
            1,
            html + line(rf"N_{{\mathrm{{общ}}}}={n}") + line(r"N_{\mathrm{благ}}=1"),
            "P",
        )
    return None
