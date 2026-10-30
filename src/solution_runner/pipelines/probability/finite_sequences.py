"""Weighted finite sequences of results, weather changes and first successes."""

import re
from datetime import date
from fractions import Fraction
from itertools import product

from solution_runner.pipelines.core.numbers import parse_rational

from .bernoulli import Trial, checked, fmt, render, result
from .common import (
    COUNT,
    NUMBER,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    require_content,
    rounding,
)

_FOOTBALL = re.compile(
    rf"Чтобы (?:пройти|выйти) в следующий круг соревнований, футбольной команде нужно набрать хотя бы (?P<goal>\d+) очк(?:а|ов) в двух играх\. Если команда выигрывает, она получает (?P<win>\d+) очк(?:а|ов), в случае ничьей — (?P<draw>\d+) очк(?:о|а|ов), если проигрывает — 0 очков\. Найдите вероятность того, что команде удастся выйти в следующий круг соревнований\. Считайте, что в каждой игре вероятности выигрыша и проигрыша одинаковы и равны (?P<p>{NUMBER})\."
)
_WEATHER = re.compile(
    rf"В Волшебной стране бывает два типа погоды: хорошая и отличная, причем погода, установившись утром, держится неизменной весь день\. Известно, что с вероятностью (?P<p>{NUMBER}) погода завтра будет такой же, как и сегодня\. (?:Сегодня )?(?P<a>\d+) (?P<month_a>[а-я]+),? погода в Волшебной стране (?P<start>хорошая|отличная)\. Найдите вероятность того, что (?P<b>\d+) (?P<month_b>[а-я]+) в Волшебной стране будет (?P<end>хорошая|отличная) погода\."
)
_TOYS = re.compile(
    rf"Маша коллекционирует принцесс из Киндер-сюрпризов\. Всего в коллекции (?P<n>\d+) разных принцесс, и они равномерно распределены, то есть в каждом очередном Киндер-сюрпризе может с равными вероятностями оказаться любая из (?P=n) принцесс\. У Маши уже есть (?P<known>{COUNT}) разн(?:ые принцессы|ых принцесс) из коллекции\. Какова вероятность того, что для получения следующей принцессы Маше придется купить еще (?P<a>\d+) или (?P<b>\d+) шоколадных яйца\?"
)
_RESTAURANT = re.compile(
    r"В одном ресторане в г\. Тамбове администратор предлагает гостям сыграть в «Шеш-беш»: гость бросает одновременно две игральные кости\. Если он выбросит комбинацию (?P<a>[1-6]) и (?P<b>[1-6]) очков хотя бы один раз из двух попыток, то получит комплемент от ресторана: чашку кофе или десерт бесплатно\. Какова вероятность получить комплемент\?"
)
_MONTHS = {
    name: i
    for i, name in enumerate(
        [
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        ],
        1,
    )
}


def football_outcomes(win, draw, p, goal):
    checked(p)
    if not 0 <= draw < win or p > Fraction(1, 2):
        raise UnsupportedCondition("invalid football scores or outcome probabilities")
    states = (("В", win, p), ("Н", draw, 1 - 2 * p), ("П", 0, p))
    return [
        (a, b, a[2] * b[2]) for a, b in product(states, repeat=2) if a[1] + b[1] >= goal
    ]


def _football(match, places):
    win, draw, goal = (int(match[k]) for k in ("win", "draw", "goal"))
    p = parse_rational(match["p"])
    outcomes = football_outcomes(win, draw, p, goal)
    html = (
        "<p>Победа и поражение равновероятны. Вероятность ничьей дополняет их сумму до единицы:</p>"
        + line(rf"P(В)=P(П)={fmt(p)},\quad P(Н)=1-2\cdot {fmt(p)}={fmt(1 - 2 * p)}")
    )
    html += "<p>Перечислим упорядоченные пары результатов, дающие нужное число очков. Игры независимы:</p>"
    for a, b, weight in outcomes:
        html += line(rf"{a[1]}+{b[1]}={a[1] + b[1]}\ge {goal}") + line(
            rf"P({a[0]}{b[0]})={fmt(a[2])}\cdot {fmt(b[2])}={fmt(weight)}"
        )
    html += "<p>Случаи несовместны, поэтому складываем их вероятности:</p>" + line(
        "P=" + ("+".join(fmt(weight) for _, _, weight in outcomes) or "0")
    )
    return result(sum((weight for _, _, weight in outcomes), Fraction(0)), html, places)


def weather_outcomes(n, p, start, end):
    checked(p)
    # shortcut: enumerate up to eight days; use the two-state transition matrix for longer horizons.
    if not 1 <= n <= 8 or start not in (0, 1) or end not in (0, 1):
        raise UnsupportedCondition("unsupported weather horizon or state")
    outcomes = []
    for path in product((0, 1), repeat=n):
        if path[-1] != end:
            continue
        previous = start
        weight = Fraction(1)
        factors = []
        for state in path:
            factor = p if state == previous else 1 - p
            weight *= factor
            factors.append(factor)
            previous = state
        outcomes.append((path, weight, factors))
    return outcomes


def _weather(match, places):
    if match["month_a"] not in _MONTHS or match["month_b"] not in _MONTHS:
        raise UnsupportedCondition("unknown calendar month")
    try:
        first = date(2001, _MONTHS[match["month_a"]], int(match["a"]))
        last = date(2001, _MONTHS[match["month_b"]], int(match["b"]))
    except ValueError as exc:
        raise UnsupportedCondition("invalid day in the weather experiment") from exc
    n = (last - first).days
    p = parse_rational(match["p"])
    start = int(match["start"] == "отличная")
    end = int(match["end"] == "отличная")
    outcomes = weather_outcomes(n, p, start, end)
    html = (
        f"<p>От начальной даты до указанной проходит {n} дней. Обозначим хорошую погоду буквой Х, отличную — О. Вероятность сохранить состояние равна p, сменить его — 1−p:</p>"
        + line(rf"p={fmt(p)},\quad 1-p={fmt(1 - p)}")
    )
    html += "<p>Перечислим последовательности с нужным последним состоянием. Вероятности переходов перемножаем, учитывая погоду предыдущего дня:</p>"
    for path, weight, factors in outcomes:
        label = "".join("О" if bit else "Х" for bit in path)
        html += line(
            r"P(\text{"
            + label
            + "})="
            + r"\cdot ".join(fmt(f) for f in factors)
            + "="
            + fmt(weight)
        )
    html += (
        "<p>Эти последовательности несовместны, поэтому их вероятности складываются:</p>"
        + line("P=" + "+".join(fmt(weight) for _, weight, _ in outcomes))
    )
    return result(sum((weight for _, weight, _ in outcomes), Fraction(0)), html, places)


def _toys(match, places):
    n, known = int(match["n"]), count(match["known"])
    attempts = sorted({int(match["a"]), int(match["b"])})
    if n <= 0 or not 0 <= known <= n or not all(1 <= k <= 100 for k in attempts):
        raise UnsupportedCondition("invalid collection size or first-success attempt")
    p, q = Fraction(n - known, n), Fraction(known, n)
    values = [q ** (k - 1) * p for k in attempts]
    html = (
        "<p>Новая принцесса появляется с вероятностью p, а уже имеющаяся — с вероятностью q:</p>"
        + line(
            rf"p=\frac{{{n - known}}}{{{n}}}={fmt(p)},\quad q=\frac{{{known}}}{{{n}}}={fmt(q)}"
        )
    )
    html += (
        "<p>Если следующая новая принцесса появляется на k-й покупке, все предыдущие покупки дают уже имеющиеся виды:</p>"
        + line(r"P(T=k)=q^{k-1}p")
    )
    for k, value in zip(attempts, values):
        html += line(rf"P(T={k})=({fmt(q)})^{{{k - 1}}}\cdot {fmt(p)}={fmt(value)}")
    html += (
        "<p>Разные номера первого успеха несовместны, поэтому складываем вероятности:</p>"
        + line("P=" + "+".join(fmt(value) for value in values))
    )
    return result(sum(values, Fraction(0)), html, places)


def _restaurant(match, places):
    a, b = int(match["a"]), int(match["b"])
    successes = sum(
        sorted(row) == sorted((a, b)) for row in product(range(1, 7), repeat=2)
    )
    p = Fraction(successes, 36)
    html = (
        "<p>За одну попытку порядок костей различается. Посчитаем упорядоченные варианты нужной комбинации:</p>"
        + line(rf"p=\frac{{{successes}}}{{36}}={fmt(p)}")
    )
    answer, methods = render(Trial(2, p, "any", style="restaurant", places=places))
    return answer, html + methods


def solve(text):
    text, places = rounding(normalize(text))
    for pattern, renderer in (
        (_FOOTBALL, _football),
        (_WEATHER, _weather),
        (_TOYS, _toys),
        (_RESTAURANT, _restaurant),
    ):
        if match := pattern.fullmatch(text):
            return renderer(match, places)
    raise UnsupportedCondition("unsupported complete finite-sequence experiment")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
