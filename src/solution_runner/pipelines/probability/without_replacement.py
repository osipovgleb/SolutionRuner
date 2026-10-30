"""Hypergeometric events and two distinguished coins split between pockets."""

import re
from fractions import Fraction
from math import comb

from . import solution_diagrams as diagrams
from .bernoulli import fmt, result
from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    rounding,
)
from .draw_tree import render_svg

_FORMS = {
    "одного": 1,
    "двух": 2,
    "двумя": 2,
    "трех": 3,
    "тремя": 3,
    "четырех": 4,
    "четырьмя": 4,
    "пяти": 5,
    "пятью": 5,
    "шести": 6,
    "шестью": 6,
    "семи": 7,
    "семью": 7,
    "восьми": 8,
    "восемью": 8,
    "девяти": 9,
    "девятью": 9,
    "десяти": 10,
    "десятью": 10,
}
_N = "(?:" + COUNT + "|" + "|".join(_FORMS) + ")"
_BALLS = re.compile(
    rf"В коробке (?P<r>\d+) красных и (?P<b>\d+) синих шара\. Случайным образом (?:(?:из коробки извлекают (?P<n1>{COUNT}) шаров\. Какова вероятность события «среди извлеченных не более (?P<k1>{_N}) красных шаров»\?)|(?:извлекают (?P<n2>{COUNT}) шара из коробки\. Какова вероятность того, что среди них окажется не более (?P<k2>{_N}) красного шара\?))"
)
_SHOTS = re.compile(
    rf"Стрелок стреляет в тире по (?P<targets>{_N}) одинаковым мишеням\. Вероятность попасть в каждую мишень при каждом выстреле одна и та же\. Чтобы сбить все (?P<same>{COUNT}) мишеней, стрелку потребовалось (?P<total>\d+) выстрелов\. Какова вероятность того, что (?:(?:первыми (?P<n1>{_N}) выстрелами стрелок сбил (?P<kind>хотя бы|меньше) (?P<k>{_N}) мишен(?:и|ей))|(?:среди первых (?P<n2>{_N}) выстрелов был хотя бы один промах))\?"
)
_BASKET = re.compile(
    rf"Чтобы забросить (?P<targets>{COUNT}) мячей в корзину на тренировке, баскетболисту потребовалось (?P<total>\d+) бросков\. Считая, что вероятность попадания в корзину при каждом броске одна и та же, найдите вероятность того, что при первых (?P<n>{_N}) бросках баскетболист попал в корзину не более (?P<k>{_N}) раза\."
)
_MARKERS = re.compile(
    r"В коробке (?P<a>\d+) синих, (?P<b>\d+) красных и (?P<c>\d+) зеленых фломастеров\. Случайным образом выбирают два фломастера\. Какова вероятность того, что окажутся выбраны один синий и один красный фломастер\?"
)
_COINS = re.compile(
    r"В кармане у Пети было 2 монеты по 5 рублей и (?P<m>\d+) монеты по 10 рублей\. Петя не глядя переложил какие-то (?P<n>\d+) монеты в другой карман\. Найдите вероятность того, что пятирублевые монеты лежат теперь в разных карманах\."
)
_COINS_SAME = re.compile(
    r"В кармане у Пети было (?P<m>\d+) монеты по рублю и 2 монеты по два рубля\. Петя, не глядя, переложил какие-то (?P<n>\d+) монеты в другой карман\. Найдите вероятность того, что обе двухрублевые монеты лежат в одном кармане\."
)

_FIRST_BLUE = re.compile(
    rf"В ящике (?P<red>{COUNT}) красных и (?P<blue>{COUNT}) синих фломастер(?:а|ов)\. Фломастеры вытаскивают по очереди в случайном порядке\. Какова вероятность того, что первый раз синий фломастер появится (?P<position>первым|вторым|третьим|четвертым|пятым) по счету\?"
)
_REUSE = {
    (4, 2, 3): "462efbf7-ad08-4997-8120-56496b1a6936",
    (3, 3, 3): "8bcf385c-36b0-450b-8f1f-04375e210941",
    (4, 6, 3): "0b898efe-7cc0-4b67-a05c-635c4501ef19",
    (7, 3, 3): "8fa4e9d0-8907-487e-a202-f39a9cf9e29c",
}
_KEY = "generated_first_blue_tree"
_ALT = "Дерево извлечения первого синего фломастера"


def _first_blue_input(text):
    match = _FIRST_BLUE.fullmatch(normalize(text))
    if match is None:
        return None
    red, blue = count(match["red"]), count(match["blue"])
    position = ("первым", "вторым", "третьим", "четвертым", "пятым").index(
        match["position"]
    ) + 1
    if blue < 1 or red < position - 1 or red + blue > 30:
        raise UnsupportedCondition(
            "the first-blue tree requires a feasible draw and at most thirty markers"
        )
    return red, blue, position


def required_assets(context):
    *_, text = diagrams.read(context)
    values = _first_blue_input(text)
    source = _REUSE.get(values)
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def diagram_specs(context):
    *_, text = diagrams.read(context)
    values = _first_blue_input(text)
    return (
        (diagrams.spec(_KEY, render_svg(*values)),)
        if values and values not in _REUSE
        else ()
    )


def integer(token):
    return _FORMS[token] if token in _FORMS else count(token)


def choose(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def hypergeometric_counts(total, good, n, predicate):
    if not 1 <= total <= 100 or not 0 <= good <= total or not 0 <= n <= total:
        raise UnsupportedCondition("invalid finite population or sample size")
    support = range(max(0, n - (total - good)), min(n, good) + 1)
    rows = [
        (k, choose(good, k) * choose(total - good, n - k), bool(predicate(k)))
        for k in support
    ]
    return choose(total, n), rows


def _hypergeometric(total, good, n, predicate, heading, places):
    denominator, rows = hypergeometric_counts(total, good, n, predicate)
    numerator = sum(weight for _, weight, selected in rows if selected)
    value = Fraction(numerator, denominator)
    html = "<p>" + heading + "</p>"
    symmetric = total == 2 * n and all(
        predicate(k) != predicate(good - k) for k, _, _ in rows
    )
    if symmetric:
        html += (
            "<p>Способ 1. Выбранная часть и остаток имеют одинаковый размер. Их обмен — взаимно однозначное соответствие, переводящее нужное событие в противоположное. Поэтому их вероятности одинаковы:</p>"
            + line(r"P(A)=P(\overline{A})")
            + line(r"2P(A)=1")
            + line(r"P(A)=\frac{1}{2}")
        )
    else:
        html += "<p>Симметрия выбранной части и остатка здесь не даёт деления вероятности пополам. Перечислим возможные количества успехов и учтём число соответствующих выборок.</p>"
    html += "<p>Таблица случаев. Для k успехов в выбранной части в остатке остаётся K−k успехов:</p><table><tbody><tr><th>k</th><th>Успехи в остатке</th><th>Число выборок</th><th>Нужный случай</th></tr>"
    for k, weight, selected in reversed(rows):
        html += f"<tr><td>{k}</td><td>{good - k}</td><td>{weight}</td><td>{'да' if selected else 'нет'}</td></tr>"
    html += (
        "</tbody></table><p>Комбинаторное решение. Все выборки одинакового размера равновозможны. Выберем k успехов и n−k неудач:</p>"
        + line(r"P(X=k)=\frac{C_K^k C_{N-K}^{n-k}}{C_N^n}")
    )
    terms = [
        rf"C_{{{good}}}^{{{k}}}C_{{{total - good}}}^{{{n - k}}}"
        for k, _, selected in rows
        if selected
    ]
    html += line(
        r"P=\frac{" + ("+".join(terms) or "0") + rf"}}{{C_{{{total}}}^{{{n}}}}}"
    ) + line(rf"P=\frac{{{numerator}}}{{{denominator}}}={fmt(value)}")
    return result(value, html, places)


def _conditional_shots(targets, total, n, kind, k, places):
    if not 1 <= targets <= total or not 1 <= n < total:
        raise UnsupportedCondition("the prefix must precede the known final success")
    predicate = {"ge": lambda x: x >= k, "le": lambda x: x <= k, "lt": lambda x: x < k}[
        kind
    ]
    heading = f"Последний, {total}-й, бросок (выстрел) — попадание. В предыдущих {total - 1} попытках было ровно {targets - 1} попаданий и {total - targets} промахов. При фиксированном общем числе попаданий их расположения равновозможны, поэтому первые {n} попыток образуют выборку без возвращения из этих позиций."
    return _hypergeometric(total - 1, targets - 1, n, predicate, heading, places)


def _markers(match, places):
    a, b, c = (int(match[k]) for k in ("a", "b", "c"))
    n = a + b + c
    if n < 2:
        raise UnsupportedCondition("two markers require a population of at least two")
    value = Fraction(2 * a * b, n * (n - 1))
    html = (
        "<p>Возможны два порядка: сначала синий, затем красный либо наоборот. После первого выбора число предметов уменьшается на один:</p>"
        + line(
            rf"P=\frac{{{a}}}{{{n}}}\cdot\frac{{{b}}}{{{n - 1}}}+\frac{{{b}}}{{{n}}}\cdot\frac{{{a}}}{{{n - 1}}}={fmt(value)}"
        )
    )
    html += (
        "<p>Другой способ. Общее число неупорядоченных пар — число сочетаний. Один предмет каждого нужного цвета выбирается по правилу произведения:</p>"
        + line(
            rf"P=\frac{{{a}\cdot {b}}}{{C_{{{n}}}^2}}=\frac{{{a * b}}}{{{choose(n, 2)}}}"
        )
    )
    return result(value, html, places)


def ordered_draw_probability(bits, good, bad):
    if sum(bits) > good or len(bits) - sum(bits) > bad:
        return Fraction(0), []
    value = Fraction(1)
    factors = []
    for bit in bits:
        total = good + bad
        available = good if bit else bad
        if total <= 0:
            raise UnsupportedCondition("the ordered draw exhausts its population")
        factor = Fraction(available, total)
        factors.append(factor)
        value *= factor
        if bit:
            good -= 1
        else:
            bad -= 1
    return value, factors


def _coins(match, same, places):
    ordinary, n = int(match["m"]), int(match["n"])
    total = ordinary + 2
    if not 1 <= n <= total <= 100:
        raise UnsupportedCondition(
            "the moved coins must be a valid subset of the pocket"
        )
    favorable = 2 * choose(ordinary, n - 1)
    denominator = choose(total, n)
    split = Fraction(favorable, denominator)
    html = "<p>Найдём сначала вероятность того, что две выделенные монеты окажутся в разных карманах. Это значит, что ровно одна из них попадёт в переложенную часть.</p>"
    html += (
        "<p>Способ 1. Зафиксируем положение первой выделенной монеты. Она находится в переложенной части с вероятностью n/N, а в оставшейся — с вероятностью (N−n)/N. Для второй монеты в противоположной части доступны соответственно N−n или n мест:</p>"
        + line(
            rf"P_{{\mathrm{{разные}}}}=\frac{{{n}}}{{{total}}}\frac{{{total - n}}}{{{total - 1}}}+\frac{{{total - n}}}{{{total}}}\frac{{{n}}}{{{total - 1}}}={fmt(split)}"
        )
    )
    html += "<p>Способ 2. Перечислим положение единственной выделенной монеты среди переложенных. Условные вероятности очередных выборов перемножаются, а несовместные порядки складываются:</p>"
    patterns = (
        [tuple(int(i == position) for i in range(n)) for position in range(n)]
        if n - 1 <= ordinary
        else []
    )
    if n <= 10:
        for bits in patterns:
            probability, factors = ordered_draw_probability(bits, 2, ordinary)
            label = "".join("В" if bit else "О" for bit in bits)
            html += line(
                r"P(\text{"
                + label
                + "})="
                + r"\cdot ".join(fmt(f) for f in factors)
                + "="
                + fmt(probability)
            )
    html += line(
        rf"P_{{\mathrm{{разные}}}}=\sum_{{j=1}}^{{{n}}}P(\text{{выделенная монета на месте }}j)={fmt(split)}"
    )
    fixed = split / n
    html += (
        "<p>Способ 3. Все допустимые позиции выделенной монеты имеют одинаковую вероятность. Найдём вероятность одного фиксированного порядка и умножим на число позиций:</p>"
        + line(rf"P_{{\mathrm{{фикс}}}}={fmt(fixed)}")
        + line(rf"P_{{\mathrm{{разные}}}}={n}\cdot {fmt(fixed)}={fmt(split)}")
    )
    html += (
        "<p>Способ 4. Выберем одну из двух выделенных монет и остальные монеты среди обычных:</p>"
        + line(
            rf"P_{{\mathrm{{разные}}}}=\frac{{C_2^1 C_{{{ordinary}}}^{{{n - 1}}}}}{{C_{{{total}}}^{{{n}}}}}=\frac{{{favorable}}}{{{denominator}}}"
        )
    )
    if same:
        html += (
            "<p>Теперь перейдём к противоположному событию — обе выделенные монеты в одном кармане:</p>"
            + line(rf"P_{{\mathrm{{одинаковые}}}}=1-{fmt(split)}")
        )
    return result(1 - split if same else split, html, places)


def solve(text):
    text = (
        normalize(text)
        .replace("Peзультат округлите", "Результат округлите")
        .replace("Рeзультат округлите", "Результат округлите")
    )
    text, places = rounding(text)
    if match := _BALLS.fullmatch(text):
        good, bad = int(match["r"]), int(match["b"])
        n = count(match["n1"] or match["n2"])
        k = integer(match["k1"] or match["k2"])
        return _hypergeometric(
            good + bad,
            good,
            n,
            lambda x: x <= k,
            "Выбор производится без возвращения. Назовём красный шар успехом, синий — неудачей.",
            places,
        )
    if match := _SHOTS.fullmatch(text):
        targets, total = integer(match["targets"]), int(match["total"])
        if targets != count(match["same"]):
            raise UnsupportedCondition("the initial and final target counts disagree")
        n = integer(match["n1"] or match["n2"])
        kind = ("ge" if match["kind"] == "хотя бы" else "lt") if match["kind"] else "lt"
        k = integer(match["k"]) if match["k"] else n
        return _conditional_shots(targets, total, n, kind, k, places)
    if match := _BASKET.fullmatch(text):
        return _conditional_shots(
            count(match["targets"]),
            int(match["total"]),
            integer(match["n"]),
            "le",
            integer(match["k"]),
            places,
        )
    if match := _MARKERS.fullmatch(text):
        return _markers(match, places)
    if match := _COINS.fullmatch(text):
        return _coins(match, False, places)
    if match := _COINS_SAME.fullmatch(text):
        return _coins(match, True, places)
    raise UnsupportedCondition(
        "unsupported complete sampling-without-replacement condition"
    )


def build_context_repair_plan(context, *, generated_solution_assets=()):
    content, condition, answer_section, solution, text = diagrams.read(context)
    if values := _first_blue_input(text):
        red, blue, position = values
        probability, _factors = ordered_draw_probability(
            (0,) * (position - 1) + (1,), blue, red
        )
        html = f"<p>Изобразим с помощью дерева возможные исходы. Чтобы первый синий фломастер появился на месте {position}, предыдущие {position - 1} должны быть красными. После каждого извлечения число оставшихся фломастеров уменьшается на один. Нужная конечная синяя вершина выделена рамкой.</p>"
        figure, key, changes = diagrams.image(
            content,
            _KEY,
            _ALT,
            source_id=_REUSE.get(values),
            svg=render_svg(*values),
            generated=generated_solution_assets,
        )
        html += (
            figure
            + "<p>Искомая вероятность равна произведению условных вероятностей вдоль этого пути:</p>"
        )
        terms = [
            rf"\frac{{{red - k}}}{{{red + blue - k}}}" for k in range(position - 1)
        ]
        terms.append(rf"\frac{{{blue}}}{{{red + blue - position + 1}}}")
        html += line("P=" + r"\cdot ".join(terms) + "=" + fmt(probability))
        answer, html = result(probability, html)
        return diagrams.repair(
            condition, answer_section, solution, answer, html, (key,), changes
        )
    if content.get("assets"):
        raise UnsupportedCondition(
            "solution images are only supported for the first-blue draw model"
        )
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
