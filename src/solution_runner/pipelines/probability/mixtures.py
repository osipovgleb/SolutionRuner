"""Two-source mixtures and inverse mixture weights with exact probabilities."""

import re
from fractions import Fraction
from math import lcm

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import parse_rational

from .bernoulli import checked, fmt, result
from .common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    normalize,
    require_content,
    rounding,
)

_EGGS = re.compile(
    rf"Агрофирма закупает куриные яйца (?:только )?в двух домашних хозяйствах\. (?:Известно, что )?(?P<a>{NUMBER})% яиц из первого хозяйства — яйца высшей категории, а из второго хозяйства — (?P<b>{NUMBER})% яиц высшей категории\. (?:Всего высшую категорию получает (?P<t1>{NUMBER})% яиц|В этой агрофирме (?P<t2>{NUMBER})% яиц высшей категории)\. Найдите вероятность того, что яйцо, купленное у этой агрофирмы, окажется из первого хозяйства\."
)
_FACTORY = re.compile(
    rf"Две фабрики выпускают одинаковые стекла для автомобильных фар\. Первая фабрика выпускает (?P<w>{NUMBER})% этих стекол, вторая — (?P<v>{NUMBER})%\.? Первая фабрика выпускает (?P<a>{NUMBER})% бракованных стекол, а вторая — (?P<b>{NUMBER})%\.? Найдите вероятность того, что случайно купленное в магазине стекло окажется бракованным\."
)
_REVOLVER = re.compile(
    rf"Ковбой Джон попадает в муху на стене с вероятностью (?P<a>{NUMBER}), если стреляет из пристрелянного револьвера\. Если Джон стреляет из непристрелянного револьвера, то он попадает в муху с вероятностью (?P<b>{NUMBER})\. На столе лежит (?P<n>\d+) револьверов, из них только (?P<m>\d+) пристрелянные\. Ковбой Джон видит на стене муху, наудачу хватает первый попавшийся револьвер и стреляет в муху\. Найдите вероятность того, что Джон промахнется\."
)
_HEPATITIS = re.compile(
    rf"Всем пациентам с подозрением на гепатит делают анализ крови\. Если анализ выявляет гепатит, то результат анализа называется положительным\. У больных гепатитом пациентов анализ дает положительный результат с вероятностью (?P<a>{NUMBER})\. Если пациент не болен гепатитом, то анализ может дать ложный положительный результат с вероятностью (?P<b>{NUMBER})\. Известно, что (?P<w>{NUMBER})% пациентов, поступающих с подозрением на гепатит, действительно больны гепатитом\. Найдите вероятность того, что результат анализа у пациента, поступившего в клинику с подозрением на гепатит, будет положительным\."
)
_BATTERY = re.compile(
    rf"Автоматическая линия изготавливает батарейки\. Вероятность того, что готовая батарейка неисправна, равна (?P<w>{NUMBER})\. Перед упаковкой каждая батарейка проходит систему контроля\. Вероятность того, что система забракует неисправную батарейку, равна (?P<a>{NUMBER})\. Вероятность того, что система по ошибке забракует исправную батарейку, равна (?P<b>{NUMBER})\. Найдите вероятность того, что случайно выбранная изготовленная батарейка будет забракована системой контроля\."
)
_PLATES = re.compile(
    rf"На фабрике керамической посуды (?P<d>{NUMBER})% произведенных тарелок имеют дефект\. При контроле качества продукции выявляется (?P<t>{NUMBER})% дефектных тарелок\. Остальные тарелки поступают в продажу\. Найдите вероятность того, что случайно выбранная при покупке тарелка не имеет дефект(?:ов|а)\."
)
_PCR = re.compile(
    rf"При подозрении на наличие некоторого заболевания пациента отправляют на ПЦР-тест\. Если заболевание действительно есть, то тест подтверждает его в (?P<a>{NUMBER})% случаев\. Если заболевания нет, то тест выявляет отсутствие заболевания в среднем в (?P<s>{NUMBER})% случаев\. Известно, что в среднем тест оказывается положительным у (?P<t>{NUMBER})% пациентов, направленных на тестирование\. При обследовании некоторого пациента врач направил его на ПЦР-тест, который оказался положительным\. Какова вероятность того, что пациент действительно имеет это заболевание\?"
)


def percent(token):
    return checked(parse_rational(token) / 100)


def total_probability(weight, a, b):
    checked(weight)
    checked(a)
    checked(b)
    return weight * a + (1 - weight) * b


def mixture_weight(a, b, total):
    checked(a)
    checked(b)
    checked(total)
    if a == b:
        raise UnsupportedCondition(
            "equal source rates do not determine their mixing weights"
        )
    return checked((total - b) / (a - b))


def _total(weight, a, b):
    value = total_probability(weight, a, b)
    html = "<p>Гипотезы H₁ и H₂ образуют полную группу: они несовместны, и одна из них обязательно наступает. Умножим вероятность каждой гипотезы на условную вероятность нужного события:</p>"
    html += line(rf"P(H_1)={fmt(weight)},\quad P(H_2)=1-P(H_1)={fmt(1 - weight)}")
    html += line(r"P(A)=P(H_1)P(A\mid H_1)+P(H_2)P(A\mid H_2)")
    html += line(rf"P(H_1\cap A)={fmt(weight)}\cdot {fmt(a)}={fmt(weight * a)}") + line(
        rf"P(H_2\cap A)={fmt(1 - weight)}\cdot {fmt(b)}={fmt((1 - weight) * b)}"
    )
    html += "<p>Случаи несовместны, поэтому складываем их вероятности:</p>" + line(
        rf"P(A)={fmt(weight * a)}+{fmt((1 - weight) * b)}"
    )
    return value, html


def _inverse(a, b, total):
    weight = mixture_weight(a, b, total)
    html = (
        "<p>Пусть x — доля первого источника, тогда доля второго равна 1−x. По формуле полной вероятности:</p>"
        + line(rf"{fmt(a)}x+{fmt(b)}(1-x)={fmt(total)}")
    )
    html += line(rf"({fmt(a)}-{fmt(b)})x={fmt(total)}-{fmt(b)}") + line(
        rf"x=\frac{{{fmt(total - b)}}}{{{fmt(a - b)}}}={fmt(weight)}"
    )
    return weight, html


def _eggs(match, parent, places):
    if not parent.strip():
        raise UnsupportedCondition(
            "the parent solution is required to retain the mixture methods"
        )
    a, b, total = (
        percent(match["a"]),
        percent(match["b"]),
        percent(match["t1"] or match["t2"]),
    )
    weight, short = _inverse(a, b, total)
    formal = (
        "<p>Обозначим высшую категорию событием A, а происхождение из хозяйств — H₁ и H₂. Их вероятности равны x и 1−x:</p>"
        + line(r"P(A)=P(A\mid H_1)P(H_1)+P(A\mid H_2)P(H_2)")
        + short
    )
    readable = (
        BeautifulSoup(parent, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
    )
    rich = "Пусть в первом хозяйстве" in readable
    if not rich:
        return result(weight, formal, places)
    html = short + "<p>Запишем тот же расчёт через условные вероятности:</p>" + formal
    html += (
        "<p>Ещё один способ. Пусть из первого хозяйства закупили u яиц, из второго — v. Уравнение для количества яиц высшей категории имеет вид:</p>"
        + line(rf"\frac{{{fmt(a)}u+{fmt(b)}v}}{{u+v}}={fmt(total)}")
        + line(rf"({fmt(a)}-{fmt(total)})u=({fmt(total)}-{fmt(b)})v")
    )
    u, v = weight.numerator, weight.denominator - weight.numerator
    html += (
        f"<p>Следовательно, количества можно взять в отношении {u}:{v}. Доля первого хозяйства равна:</p>"
        + line(rf"P(H_1)=\frac{{{u}}}{{{u}+{v}}}")
    )
    return result(weight, html, places)


def _plates(match, places):
    defect, detected = percent(match["d"]), percent(match["t"])
    good = 1 - defect
    bad = defect * (1 - detected)
    sale = good + bad
    if sale == 0:
        raise UnsupportedCondition("the quality filter leaves no plates for sale")
    value = good / sale
    html = (
        "<p>Пусть изготовлено N тарелок. В продажу поступают все качественные тарелки и невыявленные дефектные. Посчитаем их доли:</p>"
        + line(rf"N_{{\mathrm{{кач}}}}=(1-{fmt(defect)})N={fmt(good)}N")
        + line(
            rf"N_{{\mathrm{{деф,прод}}}}={fmt(defect)}(1-{fmt(detected)})N={fmt(bad)}N"
        )
        + line(rf"N_{{\mathrm{{прод}}}}=({fmt(good)}+{fmt(bad)})N={fmt(sale)}N")
    )
    html += line(rf"P=\frac{{{fmt(good)}N}}{{{fmt(sale)}N}}={fmt(value)}")
    n = lcm(1000, defect.denominator, (defect * detected).denominator)
    html += (
        f"<p>Числовая модель: возьмём {n} изготовленных тарелок. После контроля останутся качественные и пропущенные дефектные:</p>"
        + line(
            rf"N_{{\mathrm{{кач}}}}={int(good * n)},\quad N_{{\mathrm{{деф,прод}}}}={int(bad * n)}"
        )
        + line(rf"P=\frac{{{int(good * n)}}}{{{int(sale * n)}}}")
    )
    return result(value, html, places)


def _pcr(match, places):
    a, s, total = percent(match["a"]), percent(match["s"]), percent(match["t"])
    b = 1 - s
    if total == 0:
        raise UnsupportedCondition(
            "conditioning on a positive test requires a nonzero positive-test rate"
        )
    weight, html = _inverse(a, b, total)
    joint = weight * a
    posterior = joint / total
    html = (
        "<p>Пусть x — неизвестная доля заболевших. Положительный результат возможен при болезни или как ложный результат у здорового:</p>"
        + html
    )
    html += (
        "<p>По формуле Байеса найдём вероятность болезни при положительном тесте:</p>"
        + line(r"P(H_1\mid A)=\frac{P(H_1)P(A\mid H_1)}{P(A)}")
        + line(
            rf"P(H_1\mid A)=\frac{{{fmt(weight)}\cdot {fmt(a)}}}{{{fmt(total)}}}={fmt(posterior)}"
        )
    )
    u, v = weight.numerator, weight.denominator - weight.numerator
    html += (
        "<p>Другой способ. Пусть заболевших u, здоровых v. Число положительных результатов равно сумме истинных и ложных положительных:</p>"
        + line(rf"{fmt(total)}(u+v)={fmt(a)}u+{fmt(b)}v")
    )
    html += (
        f"<p>Соотношение численностей равно {u}:{v}. Среди всех положительных результатов найдём долю результатов заболевших:</p>"
        + line(rf"P=\frac{{{fmt(a)}\cdot {u}}}{{{fmt(total)}({u}+{v})}}")
    )
    return result(posterior, html, places)


def solve(text, parent_solution_html=""):
    text, places = rounding(normalize(text).replace(r"\%", "%").replace("–", "—"))
    text = re.sub(r"\s*%", "%", text)
    if match := _EGGS.fullmatch(text):
        return _eggs(match, parent_solution_html, places)
    if match := _FACTORY.fullmatch(text):
        w, v, a, b = (percent(match[k]) for k in ("w", "v", "a", "b"))
        if w + v != 1:
            raise UnsupportedCondition("the two factory shares must sum to one")
        value, html = _total(w, a, b)
        html = (
            "<p>H₁ — стекло изготовлено первой фабрикой, H₂ — второй. Событие A — стекло бракованное.</p>"
            + html
        )
        return result(value, html, places)
    if match := _REVOLVER.fullmatch(text):
        n, m = int(match["n"]), int(match["m"])
        a, b = checked(parse_rational(match["a"])), checked(parse_rational(match["b"]))
        if n <= 0 or not 0 <= m <= n:
            raise UnsupportedCondition("invalid calibrated-revolver counts")
        weight = Fraction(m, n)
        value, html = _total(weight, 1 - a, 1 - b)
        html = (
            "<p>H₁ — выбран пристрелянный револьвер, H₂ — непристрелянный. Сначала событие A означает промах.</p>"
            + html
        )
        hit, alternate = _total(weight, a, b)
        html += (
            "<p>Другой способ: теперь событие A означает попадание. Найдём его вероятность, затем перейдём к противоположному событию:</p>"
            + alternate
            + line(rf"P_{{\mathrm{{промах}}}}=1-{fmt(hit)}")
        )
        return result(value, html, places)
    if match := _HEPATITIS.fullmatch(text):
        value, html = _total(
            percent(match["w"]),
            checked(parse_rational(match["a"])),
            checked(parse_rational(match["b"])),
        )
        html = (
            "<p>H₁ — пациент болен, H₂ — здоров. Событие A — положительный результат анализа.</p>"
            + html
        )
        return result(value, html, places)
    if match := _BATTERY.fullmatch(text):
        value, html = _total(
            *(checked(parse_rational(match[k])) for k in ("w", "a", "b"))
        )
        html = (
            "<p>H₁ — батарейка неисправна, H₂ — исправна. Событие A — система контроля забраковала батарейку.</p>"
            + html
        )
        return result(value, html, places)
    if match := _PLATES.fullmatch(text):
        return _plates(match, places)
    if match := _PCR.fullmatch(text):
        return _pcr(match, places)
    raise UnsupportedCondition(
        "unsupported complete mixture or conditional-filter condition"
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text, parent_solution_html)
    return finish(condition, answer_section, solution, answer, html)
