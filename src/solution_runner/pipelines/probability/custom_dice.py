"""Bayesian die identification from fully enumerated fair physical faces."""

import re
from fractions import Fraction
from itertools import product

from .bernoulli import fmt, result
from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    require_content,
)

_PATTERN = re.compile(
    rf"Первый игральный кубик обычный, а на гранях второго кубика (?:(?:нет (?P<missing>четных|нечетных) чисел, а (?P<shown>нечетные|четные) )?числа (?P<labels>[1-6](?:, [1-6])*(?: и [1-6])?) встречаются по (?P<repeat>{COUNT}) раза)\. В остальном кубики одинаковые\. Один случайно выбранный кубик бросают два раза\. Известно, что в каком-то порядке выпали (?P<a>\d+) и (?P<b>\d+) очк(?:а|ов)\. Какова вероятность того, что бросали (?P<which>первый|второй) кубик\?"
)


def outcomes(faces, observed):
    if (
        len(faces) != 6
        or any(not 1 <= x <= 6 for x in faces)
        or len(observed) != 2
        or any(not 1 <= x <= 6 for x in observed)
    ):
        raise UnsupportedCondition(
            "two six-faced dice and valid observed face labels are required"
        )
    return [row for row in product(faces, repeat=2) if sorted(row) == sorted(observed)]


def solve(text):
    match = _PATTERN.fullmatch(normalize(text))
    if match is None:
        raise UnsupportedCondition("unsupported complete die-identification condition")
    labels = list(map(int, re.findall("[1-6]", match["labels"])))
    repeat = count(match["repeat"])
    if len(set(labels)) != len(labels) or len(labels) * repeat != 6:
        raise UnsupportedCondition(
            "the described label multiplicities must cover exactly six faces"
        )
    if match["missing"]:
        parity = 0 if match["shown"] == "четные" else 1
        if match["missing"] == ("четных" if parity == 0 else "нечетных") or any(
            x % 2 != parity for x in labels
        ):
            raise UnsupportedCondition(
                "the missing and repeated parities are inconsistent"
            )
    faces = labels * repeat
    observed = (int(match["a"]), int(match["b"]))
    m1 = len(outcomes(list(range(1, 7)), observed))
    m2 = len(outcomes(faces, observed))
    selected = m1 if match["which"] == "первый" else m2
    if m1 + m2 == 0:
        raise UnsupportedCondition("the observed pair is impossible on both dice")
    value = Fraction(selected, m1 + m2)
    p1, p2 = Fraction(m1, 36), Fraction(m2, 36)
    total = (p1 + p2) / 2
    requested = p1 if match["which"] == "первый" else p2
    index = 1 if match["which"] == "первый" else 2
    html = (
        "<p>Способ 1. Каждый кубик выбирается с вероятностью 1/2, а две физические грани — с вероятностью 1/36. Все варианты «кубик и две грани» равновозможны. Посчитаем варианты с указанной парой значений:</p>"
        + line(rf"N_1={m1},\quad N_2={m2}")
        + line(rf"P=\frac{{{selected}}}{{{m1}+{m2}}}={fmt(value)}")
    )
    html += (
        "<p>Способ 2. Найдём условные вероятности наблюдаемого события A, если выбран первый или второй кубик:</p>"
        + line(rf"P(A\mid H_1)=\frac{{{m1}}}{{36}}={fmt(p1)}")
        + line(rf"P(A\mid H_2)=\frac{{{m2}}}{{36}}={fmt(p2)}")
    )
    html += "<p>По формуле полной вероятности:</p>" + line(
        rf"P(A)=\frac{{1}}{{2}}\cdot {fmt(p1)}+\frac{{1}}{{2}}\cdot {fmt(p2)}={fmt(total)}"
    )
    html += (
        "<p>Теперь применим формулу Байеса к указанному в вопросе кубику:</p>"
        + line(
            rf"P(H_{index}\mid A)=\frac{{\frac{{1}}{{2}}\cdot {fmt(requested)}}}{{{fmt(total)}}}={fmt(value)}"
        )
    )
    html += (
        "<p>Формальная запись того же решения. Гипотезы H₁ и H₂ несовместны и равновероятны. Условная вероятность получается делением вероятности совместного события на вероятность наблюдения:</p>"
        + line(
            rf"P(H_{index}\cap A)=P(H_{index})P(A\mid H_{index})=\frac{{1}}{{2}}\cdot {fmt(requested)}"
        )
        + line(rf"P(H_{index}\mid A)=\frac{{P(H_{index}\cap A)}}{{P(A)}}")
    )
    return result(value, html)


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
