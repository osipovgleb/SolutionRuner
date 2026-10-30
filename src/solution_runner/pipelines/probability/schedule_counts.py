"""Uniform orders with a declared number of talks or performances per day."""

import re

from .common import COUNT, UnsupportedCondition, count, line
from .positions import ORDINAL, ordinal, rank

_CONFERENCE = re.compile(
    rf"Научная конференция проводится в (?P<days>\d+) дн(?:я|ей)\. Всего запланировано (?P<n>\d+) докладов(?: —|:) (?P<first>(?:в )?первые {COUNT} дня по \d+ докладов|в первый день \d+ докладов), остальные распределены поровну между (?P<a>{ORDINAL}) и (?P<b>{ORDINAL}) днями\. (?:На конференции планируется доклад профессора (?P<extra>[А-Я])\. )?Порядок докладов определяется жеребьевкой\. Какова вероятность(?: того)?, что доклад профессора (?P<prof>[А-Я])\. окажется запланированным на последний день конференции\?"
)
_CONTEST = re.compile(
    rf"Конкурс исполнителей проводится в (?P<days>\d+) дн(?:я|ей)\. Всего заявлено (?P<n>\d+) выступлений — по одному от каждой страны(?:, участвующей в конкурсе)?\. Исполнитель из (?P<country>[А-Я][А-Яа-я ]+) участвует в конкурсе\. В первый день (?:запланировано )?(?P<first>\d+) выступлен(?:ия|ий), остальные распределены поровну между оставшимися днями\. Порядок выступлений определяется жеребьевкой\. Какова вероятность(?: того)?, что выступление (?:исполнителя из|представителя) (?P=country) состоится в (?P<rank>{ORDINAL}) день конкурса\?"
)


def parse(text):
    if match := _CONFERENCE.fullmatch(text):
        days, total = int(match["days"]), int(match["n"])
        first = re.fullmatch(
            rf"(?:в )?первые (?P<days>{COUNT}) дня по (?P<daily>\d+) докладов",
            match["first"],
        )
        if first:
            scheduled_days, daily = count(first["days"]), int(first["daily"])
        else:
            scheduled_days, daily = (
                1,
                int(re.fullmatch(r"в первый день (\d+) докладов", match["first"])[1]),
            )
        if (
            days < 3
            or days - scheduled_days != 2
            or {ordinal(match["a"]), ordinal(match["b"])} != {days - 1, days}
            or (match["extra"] and match["extra"] != match["prof"])
        ):
            raise UnsupportedCondition(
                "the conference days or named professor are inconsistent"
            )
        remaining = total - scheduled_days * daily
        if remaining < 0 or remaining % 2:
            raise UnsupportedCondition(
                "talks cannot be split equally over the final two days"
            )
        favorable = remaining // 2
        html = "<p>Вычтем доклады первых дней из общего количества. Остальные доклады распределены поровну между двумя последними днями:</p>"
        html += line(
            rf"N_{{\mathrm{{первых}}}}={scheduled_days}\cdot{daily}={scheduled_days * daily}"
        )
        html += line(
            rf"N_{{\mathrm{{ост}}}}={total}-{scheduled_days * daily}={remaining}"
        )
        html += line(rf"N_{{\mathrm{{благ}}}}=\frac{{{remaining}}}{{2}}={favorable}")
        return total, favorable, html, "P"
    if match := _CONTEST.fullmatch(text):
        days, total, first = int(match["days"]), int(match["n"]), int(match["first"])
        if days < 2 or not 0 <= first <= total or (total - first) % (days - 1):
            raise UnsupportedCondition(
                "performances cannot be split equally over the remaining days"
            )
        position = rank(match["rank"], days)
        daily = (total - first) // (days - 1)
        favorable = first if position == 1 else daily
        html = "<p>Первый день выделен отдельно; остальные выступления делятся поровну между оставшимися днями:</p>"
        html += line(rf"N_{{\mathrm{{ост}}}}={total}-{first}={total - first}")
        html += line(
            rf"N_{{\mathrm{{в\ день}}}}=\frac{{{total - first}}}{{{days}-1}}={daily}"
        )
        html += (
            "<p>На указанный день приходится нужное число равновозможных мест в порядке выступлений:</p>"
            + line(rf"N_{{\mathrm{{благ}}}}={favorable}")
        )
        return total, favorable, html, "P"
    return None
