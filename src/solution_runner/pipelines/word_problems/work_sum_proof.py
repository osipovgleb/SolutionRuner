"""The three parent explanations of additive work rates."""

import sympy as sp

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section


def conversions(q):
    html = ""
    minutes = q.kind in {"work_sum_three", "work_measured_sum", "work_pairs_pumps"}
    for key, time in q.durations.items():
        if minutes and time.hours:
            html += "<p>Переведём время в минуты:</p>" + line(
                "t="
                + n(time.hours)
                + r"\cdot60+"
                + n(time.minutes)
                + "="
                + n(q.values[key])
            )
        elif not minutes and time.minutes:
            html += "<p>Переведём время в часы:</p>" + line(
                "t="
                + n(time.hours)
                + "+"
                + frac(n(time.minutes), "60")
                + "="
                + n(q.values[key])
            )
    return html


def times(a):
    return tuple(
        a.question.values[key] for key in ("t1", "t2", "t3") if key in a.question.values
    )


def horizon(values):
    return sp.Rational(sp.ilcm(*(v.p for v in values)), sp.igcd(*(v.q for v in values)))


def rates(a):
    values = times(a)
    total = sum(1 / t for t in values)
    html = "<p>Примем весь объём работы за 1. За единицу времени каждый участник выполняет долю работы, обратную его времени самостоятельной работы:</p>"
    html += line(
        r",\quad ".join(
            "v_" + str(i) + "=" + frac("1", n(t)) for i, t in enumerate(values, 1)
        )
    )
    html += (
        "<p>Производительности складываются. Найдём время выполнения всей работы:</p>"
    )
    html += line("v=" + "+".join(frac("1", n(t)) for t in values) + "=" + n(total))
    return html + line("t=" + frac("1", n(total)) + "=" + n(a.result))


def inverse(a):
    values = times(a)
    common = horizon(values)
    jobs = sum(common / t for t in values)
    html = "<p>Время работы равно отношению её объёма к скорости выполнения. Объём равен 1, а совместная производительность — сумме производительностей участников:</p>"
    html += line("t=" + frac("1", "+".join(frac("1", n(t)) for t in values)))
    html += "<p>Приведём дроби в знаменателе к общему знаменателю:</p>"
    html += line("t=" + frac(n(common), "+".join(n(common / t) for t in values)))
    return html + line("t=" + frac(n(common), n(jobs)) + "=" + n(a.result))


def common_jobs(a):
    values = times(a)
    common = horizon(values)
    jobs = tuple(common / t for t in values)
    unit = "минут" if a.question.kind == "work_sum_three" else "часов"
    html = f"<p>Возьмём общий промежуток времени, равный наименьшему общему кратному времён самостоятельной работы, в единицах {unit}:</p>"
    html += line("H=" + n(common))
    html += "<p>За это время каждый участник выполнит целое число таких работ. Сложим выполненные объёмы:</p>"
    html += line(
        "N="
        + "+".join(frac(n(common), n(t)) for t in values)
        + "="
        + "+".join(map(n, jobs))
        + "="
        + n(sum(jobs))
    )
    return (
        html
        + "<p>Чтобы найти время одной работы, разделим общий промежуток на число работ:</p>"
        + line("t=" + frac(n(common), n(sum(jobs))) + "=" + n(a.result))
    )


def proof(a):
    blocks = (
        (rates, inverse, common_jobs)
        if a.question.kind == "work_sum_two"
        else (inverse, rates, common_jobs)
    )
    titles = ("Решение", "Приведем другое решение.", "Приведем ещё одно решение.")
    return conversions(a.question) + "".join(
        section(method(a), title) for method, title in zip(blocks, titles, strict=True)
    )
