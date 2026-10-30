"""Read audited good/bad counts without confusing subtotals with totals."""

from __future__ import annotations

import re

from .common import COUNT, UnsupportedCondition, count, line

_LEAKS = re.compile(
    r"В среднем из (?P<n>\d+) садовых насосов, поступивших в продажу, (?P<bad>\d+) подтекают\. Найдите вероятность того, что один случайно выбранный для контроля насос не подтекает\."
)
_BAGS_TOTAL = re.compile(
    r"Фабрика выпускает сумки\. В среднем (?P<bad>\d+) сум(?:ок|ки|ка) из (?P<n>\d+) име(?:ют|ет) скрытые дефекты\. Найдите вероятность того, что купленная сумка окажется без дефектов\."
)
_BAGS_PARTS = re.compile(
    rf"Фабрика выпускает сумки\. В среднем на (?P<good>\d+) качественных сумок приходится (?P<bad>{COUNT}) сум(?:ок|ки|ка) со скрытыми дефектами\. Найдите вероятность того, что купленная сумка окажется качественной\."
)
_PUMPS_PARTS = re.compile(
    r"При производстве в среднем на каждые (?P<good>\d+) исправных насос(?:а|ов) приходится (?P<bad>\d+) неисправных\. Найдите вероятность того, что случайно выбранный насос окажется неисправным\."
)
_PUMPS_TOTAL = re.compile(
    r"При производстве в среднем из (?P<n>\d+) насосов (?P<bad>\d+) неисправных\. Найдите вероятность того, что случайно выбранный насос окажется неисправным\."
)
_INFANTS = re.compile(
    r"В некотором городе из (?P<n>\d+) появившихся на свет младенцев (?P<m>\d+) (?P<given>мальчиков|девочек)\. Найдите частоту рождения (?P<target>мальчиков|девочек) в этом городе\."
)


def parse(text: str):
    match = _LEAKS.fullmatch(text) or _BAGS_TOTAL.fullmatch(text)
    if match:
        n, bad = int(match["n"]), int(match["bad"])
        return (
            n,
            n - bad,
            "<p>Из общего количества исключим изделия с указанным дефектом:</p>"
            + line(rf"N_{{\mathrm{{благ}}}}={n}-{bad}={n - bad}"),
            "P",
        )
    if match := _BAGS_PARTS.fullmatch(text):
        good, bad = int(match["good"]), count(match["bad"])
        return (
            good + bad,
            good,
            "<p>Общее количество сумок включает качественные и дефектные:</p>"
            + line(rf"N_{{\mathrm{{общ}}}}={good}+{bad}={good + bad}")
            + line(rf"N_{{\mathrm{{благ}}}}={good}"),
            "P",
        )
    if match := _PUMPS_PARTS.fullmatch(text):
        good, bad = int(match["good"]), int(match["bad"])
        return (
            good + bad,
            bad,
            "<p>Сложим исправные и неисправные насосы, чтобы найти общее количество:</p>"
            + line(rf"N_{{\mathrm{{общ}}}}={good}+{bad}={good + bad}")
            + line(rf"N_{{\mathrm{{благ}}}}={bad}"),
            "P",
        )
    if match := _PUMPS_TOTAL.fullmatch(text):
        n, bad = int(match["n"]), int(match["bad"])
        return (
            n,
            bad,
            "<p>Общее количество насосов уже дано, а благоприятные исходы — выбор неисправного насоса:</p>"
            + line(rf"N_{{\mathrm{{общ}}}}={n}")
            + line(rf"N_{{\mathrm{{благ}}}}={bad}"),
            "P",
        )
    if match := _INFANTS.fullmatch(text):
        n, observed = int(match["n"]), int(match["m"])
        if not 0 <= observed <= n:
            raise UnsupportedCondition("infant subtotal exceeds the total")
        favorable = observed if match["given"] == match["target"] else n - observed
        html = "<p>Относительная частота равна отношению числа рождений указанного пола к общему числу новорождённых. Найдём нужное количество:</p>"
        html += line(
            rf"N_{{\mathrm{{благ}}}}={favorable}"
            if match["given"] == match["target"]
            else rf"N_{{\mathrm{{благ}}}}={n}-{observed}={favorable}"
        )
        return n, favorable, html, "W"
    return None
