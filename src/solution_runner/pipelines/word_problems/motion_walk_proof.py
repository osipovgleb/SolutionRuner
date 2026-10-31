"""All parent approaches to meeting a walker returning from the forest."""

from ..probability.common import line
from .common import UnsupportedCondition
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section


def direct_distance(a):
    v = a.question.values
    distance, slow, fast = (n(v[k]) for k in ("distance", "slow", "fast"))
    html = "<p>Пусть x км — искомое расстояние. Медленный путник проходит x км, а быстрый сначала доходит до опушки и затем возвращается на расстояние от неё до места встречи:</p>"
    html += line(
        "S_1=x,\\quad S_2="
        + distance
        + "+("
        + distance
        + "-x)="
        + n(2 * v["distance"])
        + "-x"
    )
    html += "<p>Времена движения путников равны:</p>"
    html += line(
        frac("x", slow) + "=" + frac(distance, fast) + "+" + frac(distance + "-x", fast)
    )
    html += line(fast + "x=" + slow + "(" + n(2 * v["distance"]) + "-x)")
    html += line(n(v["fast"] + v["slow"]) + "x=" + n(2 * v["distance"] * v["slow"]))
    return html + line("x=" + n(a.result))


def residual_distance(a):
    v = a.question.values
    distance, slow, fast = (n(v[k]) for k in ("distance", "slow", "fast"))
    residual = v["distance"] * (v["fast"] - v["slow"]) / (v["fast"] + v["slow"])
    html = "<p>Пусть x км — расстояние, которое не дошёл до опушки первый путник. Оно равно расстоянию, которое прошёл обратно от опушки второй. Путники затратили одно и то же время:</p>"
    html += line(frac(distance + "+x", fast) + "=" + frac(distance + "-x", slow))
    html += line(slow + "(" + distance + "+x)=" + fast + "(" + distance + "-x)")
    html += line(
        n(v["fast"] + v["slow"]) + "x=" + n(v["fast"] - v["slow"]) + r"\cdot" + distance
    )
    html += line("x=" + n(residual))
    html += "<p>Вычтем оставшееся до опушки расстояние из полного пути от дома до опушки:</p>"
    return html + line(distance + "-" + n(residual) + "=" + n(a.result))


def common_time(a):
    v = a.question.values
    distance, slow, fast = (n(v[k]) for k in ("distance", "slow", "fast"))
    total = 2 * v["distance"] / (v["slow"] + v["fast"])
    html = "<p>Пусть x ч — время от начала движения до встречи. Медленный путник прошёл расстояние до места встречи, а быстрый прошёл путь до опушки и часть обратного пути. Они находятся на одном и том же расстоянии от опушки:</p>"
    html += line(distance + "-" + slow + "x=" + fast + "x-" + distance)
    html += line(n(v["fast"] + v["slow"]) + "x=" + n(2 * v["distance"]))
    html += line("x=" + n(total))
    html += line("S=" + slow + r"\cdot(" + n(total) + ")=" + n(a.result))
    html += "<p><i>Комментарий.</i> По каждому участку либо прошли оба пешехода, либо один пешеход дважды. Поэтому общий пройденный путь равен удвоенному расстоянию от дома до опушки. Уравнение можно записать так:</p>"
    return html + line(fast + "x+" + slow + "x=" + n(2 * v["distance"]))


def two_stages(a):
    v = a.question.values
    first_time = v["distance"] / v["fast"]
    first_distance = v["slow"] * first_time
    gap = v["distance"] - first_distance
    approach = v["slow"] + v["fast"]
    second_time = gap / approach
    additional = v["slow"] * second_time
    html = "<p>Тот, кто идёт быстрее, дойдёт до опушки за время:</p>"
    html += line("t_1=" + frac(n(v["distance"]), n(v["fast"])) + "=" + n(first_time))
    html += "<p>За это время медленный путник пройдёт часть пути и окажется на следующем расстоянии от опушки:</p>"
    html += line(
        "S_1=" + n(v["slow"]) + r"\cdot(" + n(first_time) + ")=" + n(first_distance)
    )
    html += line("d=" + n(v["distance"]) + "-" + n(first_distance) + "=" + n(gap))
    html += "<p>После поворота они пойдут навстречу друг другу. Разделим расстояние между ними на скорость сближения:</p>"
    html += line("u=" + n(v["slow"]) + "+" + n(v["fast"]) + "=" + n(approach))
    html += line("t_2=" + frac(n(gap), n(approach)) + "=" + n(second_time))
    html += line(
        "S_2=" + n(v["slow"]) + r"\cdot(" + n(second_time) + ")=" + n(additional)
    )
    html += line("S=" + n(first_distance) + "+" + n(additional) + "=" + n(a.result))
    return html


def reflection(a):
    v = a.question.values
    total = 2 * v["distance"] / (v["slow"] + v["fast"])
    html = "<p><b>Приведём ещё одно решение.</b></p><p>Отразим путь быстрого путника относительно опушки. Условие равносильно тому, что два человека находятся по разные стороны от опушки, каждый на расстоянии от неё, равном пути от дома до опушки, и идут навстречу друг другу:</p>"
    html += line("d=2\\cdot" + n(v["distance"]) + "=" + n(2 * v["distance"]))
    html += line(
        "u=" + n(v["slow"]) + "+" + n(v["fast"]) + "=" + n(v["slow"] + v["fast"])
    )
    html += line(
        "t=" + frac(n(2 * v["distance"]), n(v["slow"] + v["fast"])) + "=" + n(total)
    )
    return html + line("S=" + n(v["slow"]) + r"\cdot(" + n(total) + ")=" + n(a.result))


def proof(a):
    v = a.question.values
    residual = v["distance"] * (v["fast"] - v["slow"]) / (v["fast"] + v["slow"])
    first_distance = v["slow"] * v["distance"] / v["fast"]
    additional = v["slow"] * (v["distance"] - first_distance) / (v["slow"] + v["fast"])
    if a.result != v["distance"] - residual or a.result != first_distance + additional:
        raise UnsupportedCondition(
            "the returning-walker methods must agree on the meeting point"
        )
    return (
        section(direct_distance(a), "Решение")
        + section(residual_distance(a), "Приведем другое решение.")
        + section(common_time(a), "Приведем другое решение.")
        + section(two_stages(a) + reflection(a), "Приведем другое решение.")
    )
