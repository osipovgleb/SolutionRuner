"""Select progression members using the interval length and the series step."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline


def progressions(a):
    from .exam_trigonometric_proof import pi, series_lines

    lo, hi, _, _ = a.bounds
    length = hi - lo
    html = (
        "<p>Отберём члены каждой периодической серии на промежутке "
        + inline(a.interval)
        + ".</p>"
    )
    for offset, period, start, end, values in a.selections:
        if period.is_Rational is not True or period <= 0:
            raise UnsupportedCondition(
                "the progression step must be a positive rational multiple of pi"
            )
        maximum = int(sp.floor(length / period)) + 1
        if len(values) > maximum:
            raise UnsupportedCondition(
                "the selected members exceed the interval-length bound"
            )
        for text in series_lines(((offset, period),)):
            html += line(text + r",\quad k\in\mathbb Z")
        html += (
            "<p>Разность между соседними членами равна "
            + inline(pi(period))
            + ". Длина промежутка равна "
            + inline(pi(length))
            + "; число членов этой серии в промежутке не превосходит "
            + str(maximum)
            + ".</p>"
        )
        if start > end:
            html += "<p>Членов этой серии в указанном промежутке нет.</p>"
        else:
            html += line(
                r"k\in\{" + ";".join(str(k) for k in range(start, end + 1)) + r"\}"
            )
            html += "<p>Подходят числа:</p>"
            for root in values:
                html += line("x=" + pi(root))
    return html
