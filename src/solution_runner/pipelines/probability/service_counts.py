"""Seats, reserve rooms and complementary taxi liveries."""

import re

from .common import UnsupportedCondition, line
from .inventory_counts import color

_AIRPLANE = re.compile(
    r"На борту самолета (?P<a>\d+) (?:кресел расположены рядом|мест рядом) с запасными выходами и (?P<b>\d+)(?: —| мест) за перегородками, разделяющими салоны\. (?:Все эти места удобны для пассажира высокого роста\. Остальные места неудобны\.|Остальные места неудобны для пассажира высокого роста\.) Пассажир (?P<person>[А-Я])\. высокого роста\. Найдите вероятность того, что на регистрации при случайном выборе места пассажиру (?P=person)\. достанется удобное место, если всего в самолете (?P<n>\d+) мест\."
)
_RESERVE = re.compile(
    r"На олимпиаде по [а-я ]+ (?P<n>\d+) участников разместили в трех аудиториях\. В первых двух удалось разместить по (?P<k>\d+) человек, оставшихся перевели в запасную аудиторию в другом корпусе\. Найдите вероятность того, что случайно выбранный участник писал олимпиаду в запасной аудитории\."
)
_LIVERY = re.compile(
    r"В фирме такси в наличии (?P<n>\d+) легковых автомобилей; (?P<k>\d+) из них (?P<car1>[а-я]+) цвета с (?P<letters1>[а-я]+) надписями на бортах, остальные — (?P<car2>[а-я]+) цвета с (?P<letters2>[а-я]+) надписями\. Найдите вероятность того, что на случайный вызов приедет машина (?P<car>[а-я]+) цвета с (?P<letters>[а-я]+) надписями\."
)


def parse(text):
    if match := _AIRPLANE.fullmatch(text):
        n, a, b = int(match["n"]), int(match["a"]), int(match["b"])
        html = "<p>Удобные места расположены в двух непересекающихся частях салона. Сложим их количества:</p>"
        return (
            n,
            a + b,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={a}+{b}={a + b}"),
            "P",
        )
    if match := _RESERVE.fullmatch(text):
        n, k = int(match["n"]), int(match["k"])
        html = "<p>Из общего количества участников вычтем тех, кто разместился в первых двух аудиториях:</p>"
        return (
            n,
            n - 2 * k,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={n}-{k}-{k}={n - 2 * k}"),
            "P",
        )
    if match := _LIVERY.fullmatch(text):
        n, k = int(match["n"]), int(match["k"])
        if not 0 <= k <= n:
            raise UnsupportedCondition("taxi subtotal exceeds the fleet")
        first = (color(match["car1"]), color(match["letters1"]))
        second = (color(match["car2"]), color(match["letters2"]))
        target = (color(match["car"]), color(match["letters"]))
        if target not in (first, second):
            raise UnsupportedCondition("the requested taxi livery is not in the fleet")
        favorable = (k if target == first else 0) + (n - k if target == second else 0)
        html = "<p>Найдём количество автомобилей с указанным сочетанием цвета кузова и надписей:</p>"
        return (
            n,
            favorable,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={favorable}"),
            "P",
        )
    return None
