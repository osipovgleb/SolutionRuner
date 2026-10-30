"""Circular seating of two girls, with slot, factorial and block methods."""

import re

from .common import UnsupportedCondition, line

_CIRCLE = re.compile(
    r"За круглый стол на (?P<n>\d+) стул(?:ьев|а)? в случайном порядке рассаживаются (?P<boys>\d+) мальчик(?:ов|а)? и 2 девочки\. Найдите вероятность того, что (?P<event>(?:обе )?девочки (?:не )?будут сидеть рядом|между девочками будет сидеть один мальчик)\."
)


def parse(text):
    match = _CIRCLE.fullmatch(text)
    if match is None:
        return None
    n, boys = int(match["n"]), int(match["boys"])
    if boys < 1 or n != boys + 2:
        raise UnsupportedCondition(
            "the chairs must match two girls and the declared boys"
        )
    separated = match["event"].startswith("между")
    complement = "не будут" in match["event"]
    distance = 2 if separated else 1
    seats = len({distance % n, (-distance) % n} - {0})
    favorable = n - 1 - seats if complement else seats
    html = "<p>Способ 1. Зафиксируем место одной девочки. Для второй равновозможны все оставшиеся места.</p>"
    html += (
        "<p>Подходят места через одно по часовой стрелке и против неё. Совпавшее место считаем один раз:</p>"
        if separated
        else "<p>Рядом с первой девочкой находятся два соседних места:</p>"
    )
    html += line(rf"Q=\frac{{{seats}}}{{{n - 1}}}")
    html += "<p>Способ 2. Пронумеруем стулья. Всего перестановок участников — n!. Выберем место первой, фиксированной девочки, затем подходящее место второй и переставим мальчиков:</p>"
    html += line(rf"N_{{\mathrm{{общ}}}}={n}!")
    html += line(rf"N_{{\mathrm{{благ}}}}={n}\cdot {seats}\cdot {boys}!")
    html += line(
        rf"Q=\frac{{{n}\cdot {seats}\cdot {boys}!}}{{{n}!}}=\frac{{{seats}}}{{{n - 1}}}"
    )
    html += "<p>Способ 3. При круговой рассадке повороты не различаются, поэтому всего имеется (n−1)! порядков.</p>"
    if separated:
        html += f"<p>Выберем одного из {boys} мальчиков между девочками и объединим их в блок. У блока два порядка девочек; остальные мальчики и блок образуют круговую рассадку:</p>"
        correction = r"\cdot 2" if n == 4 else ""
        html += line(
            rf"Q=\frac{{{boys}\cdot 2\cdot {boys - 1}!}}{{{n - 1}!{correction}}}=\frac{{{seats}}}{{{n - 1}}}"
        )
        if n == 4:
            html += "<p>При четырёх стульях между девочками по одному мальчику с обеих сторон. Каждый порядок учтён двумя выборами среднего мальчика, поэтому делим число благоприятных порядков на 2.</p>"
    else:
        html += "<p>Объединим двух девочек в один блок. Внутри блока два порядка; мальчики и блок рассаживаются по кругу:</p>"
        html += line(
            rf"Q=\frac{{2\cdot {boys}!}}{{{n - 1}!}}=\frac{{{seats}}}{{{n - 1}}}"
        )
        html += "<p>Замечание. Если n девочек и m мальчиков, где n,m ≥ 1, сидят двумя отдельными блоками, внутренние перестановки дают n!m! порядков из (n+m−1)! круговых:</p>"
        html += line(r"Q=\frac{n!m!}{(n+m-1)!}")
    html += (
        "<p>Перейдём к противоположному событию — девочки не рядом:</p>"
        if complement
        else "<p>Искомое событие совпадает с подсчитанным:</p>"
    )
    html += line(rf"P=1-Q=\frac{{{favorable}}}{{{n - 1}}}" if complement else "P=Q")
    return n - 1, favorable, html, "P"
