"""Unbiased sample variance, Chebyshev bounds and specified confidence limits."""

import re
from fractions import Fraction

from . import confidence
from .common import (
    COUNT,
    NUMBER,
    SIGNED,
    UnsupportedCondition,
    count,
    fmt,
    line,
    number,
    plan,
    result,
)

_SAMPLE = re.compile(
    rf"Случайная выборка из некоторой генеральной совокупности содержит (?P<n>{COUNT}) значений: (?P<values>.+)\. По этой выборке найдите несмещенную оценку дисперсии генеральной совокупности\."
)
_PHONE = re.compile(
    r"С помощью выборочного исследования изучают цены на смартфон определенной модели\. По данным из шести независимых салонов связи и интернет-магазинов получена следующая выборка значений: (?P<values>.+) рублей\. Сделайте по этой выборке несмещенную оценку дисперсии цен на эту модель смартфона\."
)
_CHEB = re.compile(
    rf"Про случайную величину X известно, что E(?:\(X\)| ?X)=(?P<e>{SIGNED}) и D(?:\(X\)| ?X)=(?P<d>{NUMBER})\. Найдите (?P<lower>нижнюю )?оценку вероятности события «(?P<event>.+)», которую дает неравенство Чебышева\."
)
_MEASURE = re.compile(
    rf"(?P<description>При изготовлении подшипников с номинальным внешним диаметром {NUMBER} мм стандартное отклонение внешнего диаметра равно|Средняя длина нити в мотке пряжи равна {NUMBER} м, а стандартное отклонение равно|Средняя масса упаковки наполнителя для игрушек равна {NUMBER} г, а стандартное отклонение равно|Сторона квадратной керамической плитки равна {NUMBER} см, а стандартное отклонение равно) (?P<s>{NUMBER}) (?P<unit>мм|м|г)\. При помощи неравенства Чебышева найдите верхнюю оценку вероятности события «(?P<quantity>диаметр случайно выбранного подшипника отличается от среднего значения|длина нити в случайно выбранном мотке отличается от средней|масса наполнителя в случайно выбранной упаковке отклоняется от средней|сторона случайно выбранной керамической плитки отличается от средней) более чем на (?P<t>{NUMBER}) (?P=unit)»\."
)
_POLL = re.compile(
    rf"Социологическая служба планирует провести опрос избирателей, чтобы оценить долю сторонников одного из кандидатов\. Необходимо, чтобы с вероятностью не менее γ=(?P<g>{NUMBER}) полученная частота \\overline\{{X\}} отклонялась от истинной вероятности p не более чем на δ=(?P<t>{NUMBER})\. Сколько избирателей необходимо опросить\?"
)


def sample_variance(values):
    n = len(values)
    if n < 2:
        raise UnsupportedCondition("unbiased variance needs at least two observations")
    mean = sum(values) / n
    squares = [(x - mean) ** 2 for x in values]
    ss = sum(squares)
    html = (
        "<p>Найдём объём выборки и её среднее арифметическое:</p>"
        + line(rf"n={n}")
        + line(r"\overline{x}=\frac{\sum_i x_i}{n}")
    )
    html += line(
        r"\overline{x}=\frac{"
        + "+".join("(" + fmt(x) + ")" for x in values)
        + rf"}}{{{n}}}={fmt(mean)}"
    )
    html += (
        "<p>Найдём сумму квадратов отклонений. Для несмещённой оценки делим её на n−1, а не на n:</p>"
        + line(r"S=\sum_i(x_i-\overline{x})^2")
    )
    html += line(
        "S=" + "+".join(rf"({fmt(x)}-({fmt(mean)}))^2" for x in values) + "=" + fmt(ss)
    )
    html += line(rf"D_{{\mathrm{{выб}}}}=\frac{{{fmt(ss)}}}{{{n}}}") + line(
        rf"S^2=\frac{{n}}{{n-1}}D_{{\mathrm{{выб}}}}=\frac{{{fmt(ss)}}}{{{n - 1}}}"
    )
    return result(ss / (n - 1), html, "S^2")


def chebyshev(variance, distance, lower=False):
    if variance < 0 or distance <= 0:
        raise UnsupportedCondition(
            "variance must be nonnegative and the deviation positive"
        )
    ratio = variance / (distance * distance)
    bound = max(Fraction(0), 1 - ratio) if lower else min(Fraction(1), ratio)
    html = (
        "<p>Применим неравенство Чебышёва для отклонения от математического ожидания:</p>"
        + line(r"P(|X-E(X)|\ge a)\le\frac{D(X)}{a^2}")
    )
    html += line(
        rf"\frac{{D(X)}}{{a^2}}=\frac{{{fmt(variance)}}}{{({fmt(distance)})^2}}={fmt(ratio)}"
    )
    if lower:
        html += (
            "<p>Для события внутри интервала перейдём к противоположному событию:</p>"
            + line(rf"P(|X-E(X)|<a)\ge 1-{fmt(ratio)}")
        )
    html += "<p>Учитываем, что вероятность лежит между 0 и 1. Полученная величина — оценка, а не точная вероятность.</p>"
    return result(bound, html, "L" if lower else "U")


def solve(text, tables):
    if tables:
        raise UnsupportedCondition(
            "the sample/bound condition must not contain an unparsed table"
        )
    match = _SAMPLE.fullmatch(text) or _PHONE.fullmatch(text)
    if match:
        values = [number(x) for x in re.split(", | и ", match["values"])]
        expected = count(match["n"]) if "n" in match.re.groupindex else 6
        if len(values) != expected:
            raise UnsupportedCondition("the observation count disagrees with the list")
        return sample_variance(values)
    if match := _CHEB.fullmatch(text):
        e, d = number(match["e"]), number(match["d"])
        event = match["event"].strip()
        outer = re.fullmatch(
            rf"X\\le ?(?P<l>{SIGNED}) или X\\ge ?(?P<u>{SIGNED})", event
        )
        inner = re.fullmatch(rf"(?P<l>{SIGNED})\\lt ?X\\lt ?(?P<u>{SIGNED})", event)
        selected = inner if match["lower"] else outer
        if selected is None:
            raise UnsupportedCondition(
                "the requested event does not match the bound direction"
            )
        l, u = number(selected["l"]), number(selected["u"])
        if e - l != u - e:
            raise UnsupportedCondition(
                "the event must be centered at the given expectation"
            )
        answer, html = chebyshev(d, u - e, bool(match["lower"]))
        return (
            answer,
            "<p>Границы события равноудалены от математического ожидания:</p>"
            + line(rf"a={fmt(u)}-({fmt(e)})={fmt(e)}-({fmt(l)})={fmt(u - e)}")
            + html,
        )
    if match := _MEASURE.fullmatch(text):
        prefixes = {
            "При изготовлении": ("диаметр", "мм"),
            "Средняя длина": ("длина", "м"),
            "Средняя масса": ("масса", "г"),
            "Сторона": ("сторона", "мм"),
        }
        if not any(
            match["description"].startswith(p)
            and match["quantity"].startswith(q)
            and match["unit"] == unit
            for p, (q, unit) in prefixes.items()
        ):
            raise UnsupportedCondition(
                "the measured quantity and the deviation event disagree"
            )
        s, t = number(match["s"]), number(match["t"])
        if s < 0:
            raise UnsupportedCondition("standard deviation cannot be negative")
        answer, html = chebyshev(s * s, t)
        return (
            answer,
            "<p>Номинальный размер не нужен: оцениваем отклонение от фактического среднего. Дисперсия — квадрат стандартного отклонения:</p>"
            + line(rf"D(X)=\sigma^2=({fmt(s)})^2={fmt(s * s)}")
            + html,
        )
    if confidence_answer := confidence.solve(text):
        return confidence_answer
    if match := _POLL.fullmatch(text):
        g, t = number(match["g"]), number(match["t"])
        if not 0 < g < 1 or t <= 0:
            raise UnsupportedCondition("invalid confidence level or tolerance")
        threshold = 1 / (4 * (1 - g) * t * t)
        n = -(-threshold.numerator // threshold.denominator)
        html = (
            "<p>Для доли ответов используем дисперсию среднего не больше 1/(4N). Неравенство Чебышёва даёт достаточную оценку:</p>"
            + line(r"P(|\overline{X}-p|<\delta)\ge 1-\frac{1}{4N\delta^2}")
            + line(r"1-\frac{1}{4N\delta^2}\ge\gamma")
            + line(r"N\ge\frac{1}{4(1-\gamma)\delta^2}")
            + line(rf"N\ge\frac{{1}}{{4(1-{fmt(g)})({fmt(t)})^2}}={fmt(threshold)}")
        )
        html += "<p>Число респондентов целое, поэтому округляем необходимый объём вверх:</p>"
        return result(Fraction(n), html, "N")
    raise UnsupportedCondition("unsupported complete statistical-estimate condition")


def build_context_repair_plan(context):
    return plan(context, solve)
