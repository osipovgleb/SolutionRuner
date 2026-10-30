"""Independent events with two different probabilities and two-color baskets."""

import re
from fractions import Fraction

from solution_runner.pipelines.core.numbers import parse_rational

from .bernoulli import checked, fmt, result
from .common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    normalize,
    require_content,
)

_CHESS = re.compile(
    rf"Если шахматист А\. играет белыми фигурами, то он выигрывает у шахматиста Б\. с вероятностью (?P<a>{NUMBER})\. Если А\. играет черными, то А\. выигрывает у Б\. с вероятностью (?P<b>{NUMBER})\. Шахматисты А\. и Б\. играют две партии, причем во второй партии меняют цвет фигур\. Найдите вероятность того, что А\. выиграет оба раза\."
)
_SHOP = re.compile(
    rf"По отзывам покупателей (?P<name>[А-Я][а-я]+ [А-Я][а-я]+) оценил надежность двух интернет-магазинов\. Вероятность того, что нужный товар доставят из магазина А, равна (?P<a>{NUMBER})\. Вероятность того, что этот товар доставят из магазина Б, равна (?P<b>{NUMBER})\. (?P=name) заказал товар сразу в обоих магазинах\. Считая, что интернет-магазины работают независимо друг от друга, найдите вероятность того, что ни один магазин не доставит товар\."
)
_SHOP_WEEK = re.compile(
    rf"(?P<name>[А-Я][а-я]+ [А-Я][а-я]+) выбирает интернет-магазин на основе рейтинга надежности\. Вероятность того, что нужный товар доставят из магазина A в течение недели, равна (?P<a>{NUMBER})\. Вероятность того, что нужный товар доставят из магазина B в течение недели, равна (?P<b>{NUMBER})\. (?P=name) заказал товар сразу в двух магазинах\. Считая, что интернет-магазины работают независимо друг от друга, найдите вероятность того, что ни один из магазинов не доставит товар в указанный срок\."
)
_BASKETS = re.compile(
    r"Садовник принес две корзинки фруктов\. В одной из них (?P<a>\d+) яблока и (?P<b>\d+) персиков, а в другой — (?P<c>\d+) яблок и (?P<d>\d+) персиков\. Хозяйка, не глядя, взяла из каждой корзинки по одному фрукту\. Какова вероятность того, что она достала два яблока или два персика\?"
)


def solve(text):
    text = normalize(text)
    if match := _CHESS.fullmatch(text):
        a, b = checked(parse_rational(match["a"])), checked(parse_rational(match["b"]))
        html = (
            "<p>В двух партиях шахматист по одному разу играет каждым цветом. Победы независимы, поэтому перемножаем их вероятности:</p>"
            + line(rf"P={fmt(a)}\cdot {fmt(b)}={fmt(a * b)}")
        )
        html += (
            "<p>Другой способ: учтём оба возможных порядка цветов. При любом порядке вероятность двух побед одинакова:</p>"
            + line(rf"P(A\mid C_1)={fmt(a)}\cdot {fmt(b)}")
            + line(rf"P(A\mid C_2)={fmt(b)}\cdot {fmt(a)}")
        )
        html += (
            "<p>Пусть вероятность первого порядка равна α, тогда вероятность второго — 1−α. Формула полной вероятности даёт тот же результат:</p>"
            + line(
                rf"P(A)=\alpha\cdot {fmt(a * b)}+(1-\alpha)\cdot {fmt(a * b)}={fmt(a * b)}"
            )
        )
        return result(a * b, html)
    if match := (_SHOP.fullmatch(text) or _SHOP_WEEK.fullmatch(text)):
        a, b = checked(parse_rational(match["a"])), checked(parse_rational(match["b"]))
        html = (
            "<p>Найдём вероятность недоставки из каждого магазина, затем перемножим вероятности независимых событий:</p>"
            + line(rf"q_A=1-{fmt(a)}={fmt(1 - a)}")
            + line(rf"q_B=1-{fmt(b)}={fmt(1 - b)}")
            + line(rf"P=q_Aq_B={fmt(1 - a)}\cdot {fmt(1 - b)}")
        )
        return result((1 - a) * (1 - b), html)
    if match := _BASKETS.fullmatch(text):
        a, b, c, d = (int(match[k]) for k in ("a", "b", "c", "d"))
        if a + b == 0 or c + d == 0:
            raise UnsupportedCondition("each basket must contain at least one fruit")
        apples = Fraction(a, a + b) * Fraction(c, c + d)
        peaches = Fraction(b, a + b) * Fraction(d, c + d)
        html = (
            "<p>Фрукты выбираются независимо из разных корзинок. Посчитаем вероятности двух яблок и двух персиков отдельно:</p>"
            + line(
                rf"P_{{\mathrm{{яблоки}}}}=\frac{{{a}}}{{{a + b}}}\cdot\frac{{{c}}}{{{c + d}}}={fmt(apples)}"
            )
            + line(
                rf"P_{{\mathrm{{персики}}}}=\frac{{{b}}}{{{a + b}}}\cdot\frac{{{d}}}{{{c + d}}}={fmt(peaches)}"
            )
        )
        html += "<p>Эти случаи несовместны, поэтому складываем вероятности:</p>" + line(
            rf"P={fmt(apples)}+{fmt(peaches)}"
        )
        return result(apples + peaches, html)
    raise UnsupportedCondition("unsupported complete independent-pair experiment")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
