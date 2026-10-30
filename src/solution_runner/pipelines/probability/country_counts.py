"""Country counts in uniformly randomized sports and conference orders."""

from __future__ import annotations

import re

from .common import UnsupportedCondition, line
from .positions import ORDINAL, rank

_COUNTRY = r"[А-Я][А-Яа-я ]*"
_SHOT = re.compile(
    rf"В соревнованиях по толканию ядра участвуют (?P<items>.+)\. Порядок, в котором выступают спортсмены, определяется жребием\. Найдите вероятность того, что спортсмен, который выступает (?P<rank>{ORDINAL}), окажется из (?P<target>{_COUNTRY})\."
)
_SPEAKERS = re.compile(
    rf"На конференцию приехали (?P<items>.+)\. Каждый из них делает на конференции один доклад\. Порядок докладов определяется жеребьевкой\. Найдите вероятность того, что (?P<rank>{ORDINAL}) окажется доклад ученого из (?P<target>{_COUNTRY})\."
)
_GYMNASTS = re.compile(
    rf"В чемпионате по гимнастике участвуют (?P<n>\d+) спортсменок: (?P<a>\d+) из (?P<ca>{_COUNTRY}), (?P<b>\d+) из (?P<cb>{_COUNTRY}), остальные(?: —)? из (?P<cc>{_COUNTRY})\. Порядок, в котором выступают гимнастки, определяется жребием\. Найдите вероятность того, что спортсменка, выступа(?:ющая|вшая) (?P<rank>{ORDINAL}), окажется из (?P<target>{_COUNTRY})\."
)
_DIVERS = re.compile(
    rf"На чемпионате по прыжкам в воду выступают (?P<n>\d+) спортсменов, среди них (?P<a>\d+) прыгун(?:ов|а)? из (?P<ca>{_COUNTRY}) и (?P<b>\d+) прыгун(?:ов|а)? из (?P<cb>{_COUNTRY})\. Порядок выступлений определяется жеребьевкой\. Найдите вероятность того, что (?P<rank>{ORDINAL}) будет выступать прыгун из (?P<target>{_COUNTRY})\."
)
_BIATHLON = re.compile(
    rf"В соревновании по биатлону участвуют спортсмены из (?P<countries>\d+) стран, одна из которых — {_COUNTRY}\. Всего на старт вышло (?P<n>\d+) участников, из которых (?P<m>\d+) — из (?P<country>{_COUNTRY})\. Порядок старта определяется жребием, стартуют спортсмены друг за другом\. Какова вероятность того, что (?P<rank>{ORDINAL}) стартовал спортсмен из (?P=country)\?"
)
_ATHLETES = re.compile(
    rf"В соревнованиях участвуют (?P<n>\d+) спортсменов, из которых (?P<m>\d+) — из (?P<country>{_COUNTRY})\. Найдите вероятность того, что (?P<rank>{ORDINAL}) на соревнованиях будет выступать спортсмен из (?P=country)\."
)
_PAIRS = re.compile(
    rf"Перед началом первого тура чемпионата по [а-я ]+ участников разбивают на игровые пары случайным образом с помощью жребия\. Всего в чемпионате участвует (?P<n>\d+) [а-я]+, среди которых (?P<m>\d+) спортсмен(?:ов|а)? из (?P<country>{_COUNTRY}), в том числе (?P<person>[А-Я][а-я]+ [А-Я][а-я]+)\. Найдите вероятность того, что в первом туре (?P=person) будет играть с каким-либо [а-я]+ из (?P=country)\."
)


def _counts(items, expected):
    rows = re.split(r", | и (?=\d)", items)
    if len(rows) != expected:
        raise UnsupportedCondition("the country count list has an unexpected shape")
    result = {}
    numbers = []
    for row in rows:
        match = re.fullmatch(
            rf"(?P<n>\d+)(?: спортсмен(?:а|ов)?| учен(?:ых|ый|ого))?(?: —)? из (?P<country>{_COUNTRY})",
            row,
        )
        if match is None:
            raise UnsupportedCondition("an athlete or speaker count is not understood")
        n = int(match["n"])
        result[match["country"]] = result.get(match["country"], 0) + n
        numbers.append(n)
    return result, numbers


def _result(total, sizes, target, position, setup):
    rank(position, total)
    if (
        target not in sizes
        or any(n < 0 for n in sizes.values())
        or sum(sizes.values()) > total
    ):
        raise UnsupportedCondition(
            "the selected country is absent or the counts exceed the total"
        )
    favorable = sizes[target]
    html = "<p>Порядок определяется жребием, поэтому любое место в очереди равновозможно для каждого участника. Посчитаем общее количество участников и количество из нужной страны:</p>"
    html += (
        setup
        + line(rf"N_{{\mathrm{{общ}}}}={total}")
        + line(rf"N_{{\mathrm{{благ}}}}={favorable}")
    )
    return total, favorable, html, "P"


def parse(text):
    match = _SHOT.fullmatch(text) or _SPEAKERS.fullmatch(text)
    if match:
        sizes, numbers = _counts(
            match["items"], 4 if text.startswith("В соревнованиях") else 3
        )
        total = sum(numbers)
        setup = line(r"N_{\mathrm{общ}}=" + "+".join(map(str, numbers)) + f"={total}")
        return _result(total, sizes, match["target"], match["rank"], setup)
    if match := _GYMNASTS.fullmatch(text):
        total, a, b = int(match["n"]), int(match["a"]), int(match["b"])
        if len({match["ca"], match["cb"], match["cc"]}) != 3:
            raise UnsupportedCondition("gymnast country categories must be distinct")
        sizes = {match["ca"]: a, match["cb"]: b, match["cc"]: total - a - b}
        return _result(
            total,
            sizes,
            match["target"],
            match["rank"],
            line(rf"N_{{\mathrm{{ост}}}}={total}-{a}-{b}={total - a - b}"),
        )
    if match := _DIVERS.fullmatch(text):
        total, a, b = int(match["n"]), int(match["a"]), int(match["b"])
        sizes = {match["ca"]: a}
        sizes[match["cb"]] = sizes.get(match["cb"], 0) + b
        return _result(total, sizes, match["target"], match["rank"], "")
    match = _BIATHLON.fullmatch(text) or _ATHLETES.fullmatch(text)
    if match:
        total, favorable = int(match["n"]), int(match["m"])
        if (
            "countries" in match.re.groupindex
            and not 1 <= int(match["countries"]) <= total
        ):
            raise UnsupportedCondition(
                "the number of participating countries exceeds the athletes"
            )
        return _result(
            total, {match["country"]: favorable}, match["country"], match["rank"], ""
        )
    if match := _PAIRS.fullmatch(text):
        total, same = int(match["n"]), int(match["m"])
        if total < 2 or total % 2 or not 1 <= same <= total:
            raise UnsupportedCondition(
                "a complete pairing requires an even positive population"
            )
        html = "<p>Сам участник не может быть своим соперником. Исключим его из общего количества и из числа спортсменов той же страны:</p>"
        return (
            total - 1,
            same - 1,
            html
            + line(rf"N_{{\mathrm{{общ}}}}={total}-1={total - 1}")
            + line(rf"N_{{\mathrm{{благ}}}}={same}-1={same - 1}"),
            "P",
        )
    return None
