"""Remaining work, delayed joining and recovering a missing individual rate."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section
from .work_sum_proof import conversions


def joining(a):
    q, v = a.question, a.question.values
    solo, delay = v["solo"], v["delay"]
    completed, remaining = delay / solo, 1 - delay / solo
    together = 2 / solo
    joint_time = remaining / together
    html = "<p>Рабочий выполняет долю заказа, обратную времени самостоятельной работы. Найдём, какую часть он выполнит до присоединения второго:</p>"
    html += line(
        "v="
        + frac("1", n(solo))
        + r",\quad A_1="
        + frac(n(delay), n(solo))
        + "="
        + n(completed)
    )
    html += line("A_2=1-" + n(completed) + "=" + n(remaining))
    html += "<p>После этого оставшуюся работу они выполняют вдвоём. Разделим оставшийся объём на совместную производительность:</p>"
    html += line(
        "t="
        + frac(n(remaining), frac("1", n(solo)) + "+" + frac("1", n(solo)))
        + "="
        + n(joint_time)
    )
    html += line("T=" + n(delay) + "+" + n(joint_time) + "=" + n(a.result))
    other = "<p>После работы в одиночку первый рабочий должен был бы работать ещё:</p>"
    other += line(n(solo) + "-" + n(delay) + "=" + n(solo - delay))
    other += "<p>Но к нему присоединился рабочий той же квалификации. Они стали работать вдвое быстрее, поэтому совместная часть заняла вдвое меньше времени:</p>"
    other += line("t=" + frac(n(solo - delay), "2") + "=" + n(joint_time))
    other += line("T=" + n(delay) + "+" + n(joint_time) + "=" + n(a.result))
    return (
        conversions(q)
        + section(html, "Решение")
        + section(other, "Приведем другое решение.")
    )


def missing_rate(a):
    q, v = a.question, a.question.values
    rate = 1 / v["joint"] - 1 / v["known"]
    if q.kind == "work_known_girl":
        html = f"<p>Одна {v['known_name']} за минуту пропалывает долю грядки, обратную времени её самостоятельной работы. Вместе девочки выполняют большую долю. Чтобы найти, какую долю грядки за минуту выполняет {v['asked_name']}, вычтем известную производительность из совместной:</p>"
    else:
        html = "<p>Пусть объём бассейна равен 1. Производительность первой трубы — доля бассейна, которую она наполняет за час. Вычтем её из совместной производительности двух труб:</p>"
    html += line(
        "v_{\\mathrm{общ}}="
        + frac("1", n(v["joint"]))
        + r",\quad v_{\mathrm{изв}}="
        + frac("1", n(v["known"]))
    )
    html += line(
        "v=" + frac("1", n(v["joint"])) + "-" + frac("1", n(v["known"])) + "=" + n(rate)
    )
    html += "<p>Всю работу один участник выполнит за время, обратное своей производительности:</p>"
    return html + line("t=" + frac("1", n(rate)) + "=" + n(a.result))


def missing_remaining(a):
    v = a.question.values
    known_part = v["joint"] / v["known"]
    unknown_part = 1 - known_part
    html = "<p>За время совместной работы первая труба заполнит следующую долю бассейна:</p>"
    html += line("A_1=" + frac(n(v["joint"]), n(v["known"])) + "=" + n(known_part))
    html += "<p>Остальную часть за это же время заполнит вторая труба. Найдём время наполнения целого бассейна:</p>"
    html += line("A_2=1-" + n(known_part) + "=" + n(unknown_part))
    return html + line("t=" + frac(n(v["joint"]), n(unknown_part)) + "=" + n(a.result))


def known(a):
    html = conversions(a.question)
    if a.question.kind == "work_known_girl":
        return html + missing_rate(a)
    return (
        html
        + section(missing_rate(a), "Решение")
        + section(missing_remaining(a), "Приведем другое решение.")
    )


def measured(a):
    v = a.question.values
    rate = v["volume"] / v["t1"] + v["volume"] / v["t2"]
    html = conversions(a.question)
    html += "<p>Скорость каждого насоса равна объёму воды, делённому на время. При совместной работе скорости складываются:</p>"
    html += line(
        "v="
        + frac(n(v["volume"]), n(v["t1"]))
        + "+"
        + frac(n(v["volume"]), n(v["t2"]))
        + "="
        + n(rate)
        + r"\,\mathrm{л}/\mathrm{мин}"
    )
    return (
        html
        + "<p>Разделим нужный объём воды на совместную скорость перекачивания:</p>"
        + line(
            "t=" + frac(n(v["target"]), n(rate)) + "=" + n(a.result) + r"\,\mathrm{мин}"
        )
    )
