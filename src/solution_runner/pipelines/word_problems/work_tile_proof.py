"""The parent's system, product and time-difference approaches to tiling."""

from dataclasses import replace

from ..probability.common import line
from .common import UnsupportedCondition
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section
from .motion_proof import quadratic_steps


def planned_time(a):
    v = a.question.values
    rate_factor = v["gap"] / v["delay"]
    html = "<p>Пусть плиточник планирует укладывать x квадратных метров в день в течение y дней. При большей производительности он выполнит ту же работу раньше:</p>"
    html += line(
        r"\begin{cases}xy=(x+"
        + n(v["gap"])
        + ")(y-"
        + n(v["delay"])
        + r"),\\xy="
        + n(v["amount"])
        + r".\end{cases}"
    )
    html += "<p>Из первого уравнения выразим x через y и подставим во второе:</p>"
    html += line("x=" + n(rate_factor) + "y-" + n(v["gap"]))
    html += line("(" + n(rate_factor) + "y-" + n(v["gap"]) + ")y=" + n(v["amount"]))
    html += line("y>" + n(v["delay"]))
    html += quadratic_steps(a, quantities="времени и производительности")
    return (
        html
        + "<p>Найдём запланированное число квадратных метров в день:</p>"
        + line(
            "x="
            + n(rate_factor)
            + r"\cdot"
            + n(a.root)
            + "-"
            + n(v["gap"])
            + "="
            + n(a.result)
        )
    )


def product(a):
    v = a.question.values
    html = "<p>Пусть плиточник планирует укладывать x квадратных метров в день. Тогда плановое время работы и время при большей производительности равны:</p>"
    html += line(
        "t="
        + frac(n(v["amount"]), "x")
        + r",\quad t_{\mathrm{быстрее}}="
        + frac(n(v["amount"]), "x")
        + "-"
        + n(v["delay"])
    )
    html += "<p>Умножим новую производительность на новое время, чтобы получить тот же объём работы:</p>"
    html += line(
        "(x+"
        + n(v["gap"])
        + r")\left("
        + frac(n(v["amount"]), "x")
        + "-"
        + n(v["delay"])
        + r"\right)="
        + n(v["amount"])
    )
    html += line("0<x<" + n(v["amount"] / v["delay"]))
    return html + quadratic_steps(a, quantities="времени и производительности")


def difference(a):
    v = a.question.values
    html = "<p>Пусть x квадратных метров в день — запланированная производительность. Время работы равно всему объёму, делённому на дневную производительность. Разность планового и ускоренного времени равна указанному числу дней:</p>"
    html += line(
        frac(n(v["amount"]), "x")
        + "-"
        + frac(n(v["amount"]), "x+" + n(v["gap"]))
        + "="
        + n(v["delay"])
    )
    html += line("x>0")
    return html + quadratic_steps(a, quantities="времени и производительности")


def proof(a):
    from .work_rate_models import analyze

    second = analyze(replace(a.question, kind="work_tile_product"))
    third = analyze(replace(a.question, kind="work_tile_difference"))
    if a.result != second.result or a.result != third.result:
        raise UnsupportedCondition(
            "all three tiling methods must give the same planned rate"
        )
    return (
        section(planned_time(a), "Решение")
        + section(product(second), "Приведем другое решение.")
        + section(difference(third), "Приведем ещё одно решение.")
    )
