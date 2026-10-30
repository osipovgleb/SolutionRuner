"""Uniform digits, integer ranges, clock arcs, coins and access codes."""

from __future__ import annotations

import re
from itertools import product

from .common import (
    UnsupportedCondition,
    finish,
    line,
    normalize,
    probability,
    require_content,
    rounding,
)

_KEYPAD = re.compile(
    r"На клавиатуре телефона 10 цифр, от 0 до 9\. Какова вероятность того, что случайно нажатая цифра будет (?P<event>.+)\?"
)
_NATURAL = re.compile(
    r"Из множества натуральных чисел от (?P<lo>\d+) до (?P<hi>\d+) наудачу выбирают одно число\. Какова вероятность того, что оно делится на (?P<divisor>\d+)\?"
)
_CLOCK = re.compile(
    r"Механические часы с двенадцатичасовым циферблатом в какой-то момент сломались и перестали идти\. Найдите вероятность того, что часовая стрелка остановилась, достигнув отметки (?P<start>\d+), но не дойдя до отметки (?P<end>\d+)(?: час(?:а|ов))?\."
)
_MONEY = re.compile(
    r"У (?P<genitive>[А-Я][а-я]+) в копилке лежит (?P<c1>\d+) рублев(?:ых|ая), (?P<c2>\d+) двухрублев(?:ых|ая), (?P<c5>\d+) пятирублев(?:ых|ая) и (?P<c10>\d+) десятирублев(?:ых|ая) монет(?:а|ы)?\. (?P<name>[А-Я][а-я]+) наугад достает из копилки одну монету\. Найдите вероятность того, что оставшаяся в копилке сумма составит (?P<comparison>более|менее) (?P<threshold>\d+) рублей\."
)
_CODE = re.compile(
    r"Для подтверждения скидки магазин отправляет покупателю на телефон сообщение с трехзначным кодом, (?P<kind>ровно две из цифр которого совпадают|все цифры которого различны и нечетны)\. У [А-Я][а-я]+ разряжен телефон\. Какова вероятность того, что он случайно угадает код\?"
)


def _keypad(match, places):
    event = match["event"]
    if event in ("четной", "нечетной"):
        parity = int(event == "нечетной")
        favorable = [digit for digit in range(10) if digit % 2 == parity]
    elif re.fullmatch(r"[0-9]", event):
        favorable = [int(event)]
    elif bounds := re.fullmatch(r"больше (?P<lo>\d+), но меньше (?P<hi>\d+)", event):
        favorable = [
            digit
            for digit in range(10)
            if int(bounds["lo"]) < digit < int(bounds["hi"])
        ]
    else:
        raise UnsupportedCondition("unsupported complete digit event")
    html = (
        "<p>На клавиатуре десять равновозможных цифр: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9.</p>"
        + line(r"N_{\mathrm{общ}}=10")
    )
    html += (
        "<p>Условию подходят цифры: "
        + (", ".join(map(str, favorable)) or "нет")
        + ".</p>"
    )
    html += line(rf"N_{{\mathrm{{благ}}}}={len(favorable)}")
    answer, calculation = probability(len(favorable), 10, places)
    return answer, html + calculation


def _natural(match, places):
    lo, hi, divisor = (int(match[key]) for key in ("lo", "hi", "divisor"))
    if lo < 1 or hi < lo or divisor < 1:
        raise UnsupportedCondition("invalid natural-number interval or divisor")
    total = hi - lo + 1
    m = hi // divisor - (lo - 1) // divisor
    first = ((lo + divisor - 1) // divisor) * divisor
    multiples = list(range(first, hi + 1, divisor)) if m <= 30 else None
    html = "<p>Обе границы включены в диапазон. Найдём общее количество натуральных чисел:</p>"
    html += line(rf"N_{{\mathrm{{общ}}}}={hi}-{lo}+1={total}")
    html += "<p>Делимость означает делимость без остатка. "
    html += (
        "Подходящие числа: " + (", ".join(map(str, multiples)) or "нет") + ".</p>"
        if multiples is not None
        else "Количество кратных найдём по целым частям:</p>"
    )
    html += line(
        rf"N_{{\mathrm{{благ}}}}=\left\lfloor\frac{{{hi}}}{{{divisor}}}\right\rfloor-\left\lfloor\frac{{{lo - 1}}}{{{divisor}}}\right\rfloor={m}"
    )
    answer, calculation = probability(m, total, places)
    return answer, html + calculation


def _clock(match, places):
    start, end = int(match["start"]), int(match["end"])
    if not 1 <= start <= 12 or not 1 <= end <= 12 or start == end:
        raise UnsupportedCondition(
            "clock marks must specify one unambiguous forward arc"
        )
    distance = (end - start) % 12
    difference = f"{end}-{start}" if end > start else f"(12-{start})+{end}"
    html = (
        "<p>Всего на двенадцатичасовом циферблате двенадцать равных часовых делений:</p>"
        + line(r"N_{\mathrm{общ}}=12")
    )
    html += (
        "<p>Посчитаем деления между указанными отметками по ходу часовой стрелки:</p>"
    )
    html += line(rf"N_{{\mathrm{{благ}}}}={difference}={distance}")
    answer, calculation = probability(distance, 12, places)
    return answer, html + calculation


def _money(match, places):
    name, genitive = match["name"], match["genitive"]
    if genitive != name + "а" and genitive[:-1] != name[:-1]:
        raise UnsupportedCondition("coin counts and the draw refer to different people")
    amounts = {
        denomination: int(match[f"c{denomination}"]) for denomination in (1, 2, 5, 10)
    }
    total = sum(amounts.values())
    value = sum(denomination * amount for denomination, amount in amounts.items())
    threshold = int(match["threshold"])
    greater = match["comparison"] == "более"
    selected = [
        d
        for d, amount in amounts.items()
        if amount and (value - d > threshold if greater else value - d < threshold)
    ]
    m = sum(amounts[d] for d in selected)
    html = "<p>Посчитаем количество монет и общую сумму в копилке:</p>"
    html += line(
        r"N_{\mathrm{общ}}=" + "+".join(map(str, amounts.values())) + f"={total}"
    )
    html += line(
        "S=" + "+".join(rf"{n}\cdot {d}" for d, n in amounts.items()) + f"={value}"
    )
    comparison = ">" if greater else "<"
    html += "<p>Если достать монету номиналом d рублей, в копилке останется S−d рублей. Требуется:</p>"
    html += line(rf"{value}-d{comparison}{threshold}")
    html += (
        "<p>Подходят номиналы: " + (", ".join(map(str, selected)) or "нет") + ".</p>"
    )
    html += line(
        r"N_{\mathrm{благ}}="
        + ("+".join(str(amounts[d]) for d in selected) or "0")
        + f"={m}"
    )
    answer, calculation = probability(m, total, places)
    return answer, html + calculation


def _code(match, places):
    paired = match["kind"].startswith("ровно")
    domain = [
        digits
        for digits in product(range(10), repeat=3)
        if (
            sorted(digits.count(d) for d in set(digits)) == [1, 2]
            if paired
            else len(set(digits)) == 3 and all(d % 2 for d in digits)
        )
    ]
    total = len(domain)
    if paired:
        html = "<p>Повторяющуюся цифру можно выбрать десятью способами, отличную от неё — девятью. Коды могут начинаться с нуля.</p>"
        html += line(r"N_{\mathrm{наборов}}=10\cdot9=90")
        html += "<p>Отличающаяся цифра может стоять в любой из трёх позиций:</p>"
        html += line(rf"N_{{\mathrm{{общ}}}}=90\cdot3={total}")
    else:
        html = "<p>Нечётных цифр пять: 1, 3, 5, 7, 9. Поскольку цифры кода различны, для следующих позиций выбор уменьшается:</p>"
        html += line(r"N_1=5,\quad N_2=4,\quad N_3=3")
        html += line(rf"N_{{\mathrm{{общ}}}}=5\cdot4\cdot3={total}")
    html += "<p>Угадать нужно один определённый код из всех допустимых:</p>" + line(
        r"N_{\mathrm{благ}}=1"
    )
    answer, calculation = probability(1, total, places)
    return answer, html + calculation


def solve(text: str) -> tuple[str, str]:
    text, places = rounding(normalize(text))
    for pattern, renderer in (
        (_KEYPAD, _keypad),
        (_NATURAL, _natural),
        (_CLOCK, _clock),
        (_MONEY, _money),
        (_CODE, _code),
    ):
        match = pattern.fullmatch(text)
        if match:
            return renderer(match, places)
    raise UnsupportedCondition("unsupported complete uniform-outcome condition")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(
        context, allow_inline_latex=True
    )
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
