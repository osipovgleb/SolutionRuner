"""Overtaking freighters shift by both ship lengths and both clear gaps."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n


def cargo_pass(a):
    q, v = a.question, a.question.values
    metres = 1000 * a.displacement
    minutes = q.time.total_seconds / 60
    html = "<p>Чтобы сухогрузы перешли из первого положения во второе, второй должен переместиться относительно первого на сумму длин обоих судов и двух указанных расстояний между кормой и носом:</p>"
    html += line(
        "S="
        + "+".join(
            n(v[k]) for k in ("first_length", "start_gap", "second_length", "end_gap")
        )
        + "="
        + n(metres)
        + r"\,\mathrm{м}"
    )
    if q.time.seconds:
        html += line(
            "t="
            + n(q.time.minutes)
            + "+"
            + frac(n(q.time.seconds), "60")
            + "="
            + n(minutes)
            + r"\,\mathrm{мин}"
        )
    html += "<p>Разность скоростей равна относительному перемещению, делённому на время. Переведём метры в минуту в километры в час:</p>"
    html += line(
        "u="
        + frac(n(metres), n(minutes))
        + "="
        + n(metres / minutes)
        + r"\,\mathrm{м}/\mathrm{мин}"
    )
    return html + line(
        "u="
        + n(metres / minutes)
        + r"\cdot\frac{60}{1000}="
        + n(a.result)
        + r"\,\mathrm{км}/\mathrm{ч}"
    )
