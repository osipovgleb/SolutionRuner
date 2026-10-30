"""Relative orders and equally sized groups, retaining each parent method."""

import re
from html import escape
from itertools import permutations

from .common import UnsupportedCondition, line

_FESTIVAL = re.compile(
    r"На рок-фестивале выступают группы — по одной от каждой из заявленных стран\. Порядок выступления определяется жребием\. Какова вероятность того, что группа из (?P<a>[А-Я][а-я]+) будет выступать после группы из (?P<b>[А-Я][а-я]+) и после группы из (?P<c>[А-Я][а-я]+)\?"
)
_FRIENDS = re.compile(
    r"В классе (?P<n>\d+) учащи(?:хся|йся), среди них (?:два друга|две подруги) — (?P<a>[А-Я][а-я]+) и (?P<b>[А-Я][а-я]+)\. (?:Учащихся|Класс) случайным образом разбивают на (?P<r>\d+) равн(?:ые группы|ых групп)\. Найдите вероятность того, что (?P=a) и (?P=b) окажутся в одной группе\."
)


def _festival(match):
    countries = [match[key] for key in ("a", "b", "c")]
    if len(set(countries)) != 3:
        raise UnsupportedCondition(
            "the three relative-order countries must be distinct"
        )
    # Numbered labels remain distinct even when country initials coincide.
    labels = ", ".join(
        f"{i} — группа из {escape(country)}" for i, country in enumerate(countries, 1)
    )
    orders = list(permutations((1, 2, 3)))
    selected = [row for row in orders if row[-1] == 1]

    def display(rows):
        return "; ".join("…" + "…".join(map(str, row)) + "…" for row in rows)

    html = f"<p>Общее число участников фестиваля не влияет на взаимный порядок трёх указанных групп. Обозначим: {labels}.</p>"
    html += f"<p>Шесть равновозможных взаимных порядков: {display(orders)}.</p>"
    html += f"<p>Группа 1 находится после двух остальных в случаях: {display(selected)}.</p>"
    html += line(r"P=\frac{2}{6}=\frac{1}{3}")
    html += "<p>Замечание. Среди n групп из разных стран фиксированная группа оказывается последней в (n−1)! перестановках из n! возможных:</p>"
    html += line(r"P=\frac{(n-1)!}{n!}=\frac{1}{n}")
    return 6, 2, html, "P"


def _friends(match):
    n, groups = int(match["n"]), int(match["r"])
    if groups < 2 or n % groups or n // groups < 2 or match["a"] == match["b"]:
        raise UnsupportedCondition(
            "friends require distinct people and equal groups with at least two places"
        )
    size = n // groups
    a, b = escape(match["a"]), escape(match["b"])
    ratio = rf"\frac{{{size - 1}}}{{{n - 1}}}"
    html = f"<p>Способ 1. Зафиксируем группу первого участника. Из {n - 1} оставшихся мест {size - 1} находятся в той же группе. Каждый оставшийся участник равновероятно занимает одно из них:</p>"
    html += line("P=" + ratio)
    html += f"<p>Способ 2. Пусть {a} уже находится в своей группе. Участник {b} может занять любое из {n - 1} свободных мест, из которых {size - 1} — в той же группе:</p>"
    html += line(rf"P={size - 1}:{n - 1}=" + ratio)
    html += f"<p>Способ 3. Рассмотрим одну обозначенную группу из {size} человек. Всего способов выбрать её состав — число сочетаний. Для попадания обоих участников в неё выберем ещё {size - 2} человек из остальных {n - 2}. События попадания пары в каждую из {groups} групп несовместны:</p>"
    html += line(
        rf"P={groups}\cdot\frac{{C_{{{n - 2}}}^{{{size - 2}}}}}{{C_{{{n}}}^{{{size}}}}}"
    )
    html += line(
        rf"P=\frac{{{groups}\cdot {size}\cdot {size - 1}}}{{{n}\cdot {n - 1}}}=" + ratio
    )
    html += "<p>Способ 4. Умножим вероятность попадания первого участника в одну обозначенную группу на условную вероятность попадания туда второго. Затем сложим вероятности для всех равноправных групп:</p>"
    html += line(rf"P={groups}\cdot\frac{{{size}}}{{{n}}}\cdot {ratio}={ratio}")
    html += f"<p>Способ 5. Набираем к первому участнику ещё {size - 1} человек. Чтобы второй участник не попал в группу, на каждом шаге выбираем кого-либо другого. Получается сокращающееся произведение:</p>"
    html += line(
        rf"Q=\prod_{{j=0}}^{{{size - 2}}}\frac{{{n - 2}-j}}{{{n - 1}-j}}=\frac{{{n - size}}}{{{n - 1}}}"
    )
    html += "<p>Перейдём к противоположному событию:</p>"
    html += line(rf"P=1-Q=1-\frac{{{n - size}}}{{{n - 1}}}={ratio}")
    return n - 1, size - 1, html, "P"


def parse(text):
    if match := _FESTIVAL.fullmatch(text):
        return _festival(match)
    if match := _FRIENDS.fullmatch(text):
        return _friends(match)
    return None
