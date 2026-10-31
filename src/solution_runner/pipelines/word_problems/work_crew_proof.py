"""All three parent crew-transfer methods, with the actual requested period."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section


def result(a):
    v = a.question.values
    if v["include_initial"]:
        return (
            "<p>В условии требуется всё время выполнения работы, поэтому прибавим первоначальный этап:</p>"
            + line("T=" + n(v["initial"]) + "+" + n(a.root) + "=" + n(a.result))
        )
    return "<p>В условии требуется только время работы в новом составе:</p>" + line(
        "y=" + n(a.result)
    )


def system(a):
    v = a.question.values
    h, first, second, moved = (v[k] for k in ("initial", "first", "second", "transfer"))
    one, two = first + moved, second - moved
    full = first * h + one * a.root
    html = "<p>Пусть производительность каждого рабочего равна 1/x работы в день, а y дней бригады работали в новом составе. Каждая бригада выполнила одну целую работу:</p>"
    html += line(
        r"\begin{cases}"
        + frac(n(first) + r"\cdot" + n(h), "x")
        + "+"
        + frac(n(one) + "y", "x")
        + r"=1,\\"
        + frac(n(second) + r"\cdot" + n(h), "x")
        + "+"
        + frac(n(two) + "y", "x")
        + r"=1.\end{cases}"
    )
    html += "<p>Умножим оба уравнения на положительное x и приравняем выражения:</p>"
    html += line(
        n(first * h) + "+" + n(one) + "y=" + n(second * h) + "+" + n(two) + "y"
    )
    html += line(n(one - two) + "y=" + n((second - first) * h))
    html += line("y=" + n(a.root) + r",\quad x=" + n(full))
    return html + result(a)


def equal_jobs(a):
    v = a.question.values
    h, first, second, moved = (v[k] for k in ("initial", "first", "second", "transfer"))
    one, two = first + moved, second - moved
    html = "<p>Пусть k — производительность одного рабочего, y дней — работа после перехода. Общий объём первой и второй работы одинаков. Производительность k положительна, поэтому её можно сократить:</p>"
    html += line(
        n(first)
        + "k\\cdot"
        + n(h)
        + "+"
        + n(one)
        + "ky="
        + n(second)
        + "k\\cdot"
        + n(h)
        + "+"
        + n(two)
        + "ky"
    )
    html += line(
        n(first * h) + "+" + n(one) + "y=" + n(second * h) + "+" + n(two) + "y"
    )
    html += line("y=" + frac(n((second - first) * h), n(one - two)) + "=" + n(a.root))
    return html + result(a)


def person_days(a):
    v = a.question.values
    gap = (v["second"] - v["first"]) * v["initial"]
    one, two = v["first"] + v["transfer"], v["second"] - v["transfer"]
    html = "<p>До перехода вторая бригада выполнила больше работы. Выразим этот отрыв в человеко-днях:</p>"
    html += line(
        "D=("
        + n(v["second"])
        + "-"
        + n(v["first"])
        + ")\\cdot"
        + n(v["initial"])
        + "="
        + n(gap)
    )
    html += "<p>После перехода первая бригада должна выполнить на этот объём больше второй за то же время. Найдём число дней y:</p>"
    html += line(n(one) + "y=" + n(two) + "y+" + n(gap))
    html += line("y=" + frac(n(gap), n(one - two)) + "=" + n(a.root))
    return html + result(a)


def proof(a):
    return (
        section(system(a), "Решение")
        + section(equal_jobs(a), "Приведем другое решение.")
        + section(person_days(a), "Приведем ещё одно решение.")
    )
