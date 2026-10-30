"""Counts of disjoint kinds, including two equally numerous unknown kinds."""

from __future__ import annotations

import re

from .common import COUNT, UnsupportedCondition, count, line

_COLOR_ROOTS = {
    "черн",
    "бел",
    "красн",
    "желт",
    "зелен",
    "син",
    "голуб",
    "фиолетов",
    "сер",
    "оранжев",
    "розов",
    "коричнев",
}


def color(token):
    for ending in (
        "его",
        "ого",
        "ыми",
        "ых",
        "их",
        "ое",
        "ее",
        "ые",
        "ие",
        "ая",
        "ую",
        "ый",
        "ий",
        "ой",
    ):
        if token.endswith(ending) and token[: -len(ending)] in _COLOR_ROOTS:
            return token[: -len(ending)]
    raise UnsupportedCondition("unsupported color adjective")


def _entries(text, pattern, expected):
    pieces = re.split(r", | и (?=\d)", text)
    if len(pieces) != expected:
        raise UnsupportedCondition(
            "the declared number of inventory kinds is inconsistent"
        )
    rows = []
    for piece in pieces:
        match = re.fullmatch(pattern, piece)
        if match is None:
            raise UnsupportedCondition("inventory item is outside the audited grammar")
        rows.append((int(match["n"]), match["label"]))
    return rows


_TAXI = re.compile(
    r"В фирме такси в данный момент свободно (?P<n>\d+) машин: (?P<items>.+)\. По вызову выехала одна из машин, случайно оказавшаяся ближе всего к заказчице\. Найдите вероятность того, что к ней приедет (?P<neg>не )?(?P<target>[а-я]+) такси\."
)
_PIES = re.compile(
    r"(?:На тарелке|В блюде) (?P<n>\d+) пирожков: (?P<items>.+)\. [А-Я][а-я]+ наугад выбирает один пирожок\. Найдите вероятность того, что он окажется с (?P<target>[а-я ]+)\."
)
_GIFTS = re.compile(
    r"Родительский комитет закупил (?P<n>\d+) пазлов для подарков детям на окончание учебного года, из них (?P<a>\d+) с (?P<first>картинками известных художников|изображениями животных|персонажами мультфильмов|видами природы) и (?P<b>\d+) с (?P<second>картинками известных художников|изображениями животных|персонажами мультфильмов|видами природы)\. Подарки распределяются случайным образом\. Найдите вероятность того, что [А-Я][а-я]+ достанется пазл с (?P<target>животным|персонажем мультфильма|персонажем мультфильмов|видом природы|картиной известного художника)\."
)
_GIFT_LABELS = {
    "животным": "изображениями животных",
    "персонажем мультфильмов": "персонажами мультфильмов",
    "персонажем мультфильма": "персонажами мультфильмов",
    "видом природы": "видами природы",
    "картиной известного художника": "картинками известных художников",
}
_NOTEBOOKS = re.compile(
    rf"В стопке лежат школьные тетради в одинаковых [а-я]+ обложках\. (?P<a>{COUNT}) из них (?P<la>в косую линейку|в обычную линейку|в крупную клетку|в обычную клетку), (?P<b>{COUNT}) (?P<lb>в косую линейку|в обычную линейку|в крупную клетку|в обычную клетку), (?P<c>{COUNT}) (?P<lc>в косую линейку|в обычную линейку|в крупную клетку|в обычную клетку) и (?P<d>{COUNT}) (?P<ld>в косую линейку|в обычную линейку|в крупную клетку|в обычную клетку)\. Найдите вероятность того, что взятая случайным образом из этой стопки тетрадь окажется (?P<target>в косую линейку|в обычную линейку|в крупную клетку|в обычную клетку)\.",
    re.IGNORECASE,
)
_BALLOONS = re.compile(
    r"В праздничном наборе (?P<n>\d+) шариков: (?P<a>\d+) (?P<la>[а-я]+), (?P<b>\d+) (?P<lb>[а-я]+), остальные (?P<lc>[а-я]+) и (?P<ld>[а-я]+), их поровну\. Какова вероятность того, что из набора достали один шарик (?P<x>[а-я]+) или (?P<y>[а-я]+) цвета\?"
)
_BUTTONS = re.compile(
    r"В коробке лежат (?P<lc>[а-я]+) пуговицы, столько же (?P<ld>[а-я]+), (?P<a>\d+) (?P<la>[а-я]+) и (?P<b>\d+) (?P<lb>[а-я]+) — всего (?P<n>\d+) пуговиц\. Портной достает из коробки одну случайную пуговицу\. Какова вероятность того, что она окажется (?P<x>[а-я]+) или (?P<y>[а-я]+)\?"
)


def _render(total, rows, target, *, complement=False):
    if sum(n for n, _ in rows) != total:
        raise UnsupportedCondition(
            "inventory subtotals do not equal the declared total"
        )
    if target not in {label for _, label in rows}:
        raise UnsupportedCondition("the selected kind is not among the declared kinds")
    selected = sum(n for n, label in rows if label == target)
    favorable = total - selected if complement else selected
    html = "<p>Сложим количества всех видов и найдём число предметов, подходящих условию:</p>"
    html += line(r"N_{\mathrm{общ}}=" + "+".join(str(n) for n, _ in rows) + f"={total}")
    html += line(
        rf"N_{{\mathrm{{благ}}}}={total}-{selected}={favorable}"
        if complement
        else rf"N_{{\mathrm{{благ}}}}={favorable}"
    )
    return total, favorable, html, "P"


def _equal_colors(match):
    total, a, b = int(match["n"]), int(match["a"]), int(match["b"])
    remainder = total - a - b
    if remainder < 0 or remainder % 2:
        raise UnsupportedCondition("equal color counts must be nonnegative integers")
    labels = [color(match[key]) for key in ("la", "lb", "lc", "ld")]
    if len(set(labels)) != 4:
        raise UnsupportedCondition("color categories must be distinct")
    sizes = dict(zip(labels, (a, b, remainder // 2, remainder // 2)))
    targets = {color(match["x"]), color(match["y"])}
    if not targets <= sizes.keys():
        raise UnsupportedCondition("selected colors are absent from the inventory")
    favorable = sum(sizes[label] for label in targets)
    html = "<p>Оставшиеся два вида представлены поровну. Найдём количество каждого из них:</p>"
    html += line(rf"N_{{\mathrm{{ост}}}}={total}-{a}-{b}={remainder}")
    html += line(
        rf"N_{{\mathrm{{каждого}}}}=\frac{{{remainder}}}{{2}}={remainder // 2}"
    )
    html += "<p>Выбор разных цветов — несовместные события, поэтому складываем количества нужных цветов:</p>"
    html += line(
        r"N_{\mathrm{благ}}="
        + "+".join(str(sizes[label]) for label in labels if label in targets)
        + f"={favorable}"
    )
    return total, favorable, html, "P"


def parse(text):
    if match := _TAXI.fullmatch(text):
        rows = _entries(match["items"], r"(?P<n>\d+) (?P<label>[а-я]+)", 3)
        rows = [(n, color(label)) for n, label in rows]
        return _render(
            int(match["n"]), rows, color(match["target"]), complement=bool(match["neg"])
        )
    if match := _PIES.fullmatch(text):
        rows = _entries(match["items"], r"(?P<n>\d+) с (?P<label>[а-я ]+)", 3)
        return _render(int(match["n"]), rows, match["target"])
    if match := _GIFTS.fullmatch(text):
        return _render(
            int(match["n"]),
            [(int(match["a"]), match["first"]), (int(match["b"]), match["second"])],
            _GIFT_LABELS[match["target"]],
        )
    if match := _NOTEBOOKS.fullmatch(text):
        rows = [
            (count(match[key]), match["l" + key].lower())
            for key in ("a", "b", "c", "d")
        ]
        return _render(sum(n for n, _ in rows), rows, match["target"].lower())
    match = _BALLOONS.fullmatch(text) or _BUTTONS.fullmatch(text)
    return _equal_colors(match) if match else None
