"""Water-trip parent methods with the shared balance and physical domains."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_proof import conversions, quadratic_steps
from .water_algebra import (
    cleared_equation,
    even_steps,
    square_completion,
    square_steps,
    vieta,
)
from .water_balances import CURRENT_KINDS


def time_budget(q):
    html = conversions(q)
    if q.kind == "water_raft":
        total = q.values["raft_distance"] / q.values["known"]
        moving = total - q.durations["delay"].total
        html += "<p>Время движения плота равно пройденному им расстоянию, делённому на скорость течения. Яхта отправилась позже:</p>"
        html += line(
            "T_{\\mathrm{плот}}="
            + frac(n(q.values["raft_distance"]), n(q.values["known"]))
            + "="
            + n(total)
        )
        html += line(
            "T_{\\mathrm{яхта}}="
            + n(total)
            + "-"
            + n(q.durations["delay"].total)
            + "="
            + n(moving)
        )
    elif "moving" in q.durations:
        total, stop, moving = (
            q.durations[k].total for k in ("elapsed", "stop", "moving")
        )
        if "start_minute" in q.values:
            html += "<p>Возвращение произошло в тот же день. Найдём прошедшее от отправления до возвращения время:</p>"
            html += line(
                "T="
                + n(q.values["end_minute"] / 60)
                + "-"
                + n(q.values["start_minute"] / 60)
                + "="
                + n(total)
            )
        html += "<p>Вычтем время стоянки из полного времени рейса, чтобы получить время движения:</p>"
        html += line("T_{\\mathrm{дв}}=" + n(total) + "-" + n(stop) + "=" + n(moving))
    return html


def stream_setup(a):
    q = a.question
    known = n(q.values["known"])
    if q.kind in CURRENT_KINDS:
        html = (
            "<p>Пусть u км/ч — скорость течения реки. Тогда скорости "
            + q.actor
            + " по течению и против течения равны:</p>"
        )
        down, up = known + "+u", known + "-u"
        bound = "0<u<" + known
    else:
        html = (
            "<p>Пусть u км/ч — собственная скорость "
            + q.actor
            + ". Тогда скорости по течению и против течения равны:</p>"
        )
        down, up = "u+" + known, "u-" + known
        bound = "u>" + known
    html += line(r"v_{\mathrm{по}}=" + down + r",\quad v_{\mathrm{против}}=" + up)
    html += line(bound)
    return html, up, down


def stream(a):
    q, v = a.question, a.question.values
    html = ""
    if q.kind == "water_raft":
        html += "<p>Скорость плота равна скорости течения реки:</p>" + line(
            "v_{\\mathrm{плот}}=" + n(v["known"])
        )
    setup, up, down = stream_setup(a)
    html += setup + time_budget(q)
    term_up, term_down = frac(n(v["distance"]), up), frac(n(v["distance"]), down)
    if q.kind.endswith("_difference"):
        html += "<p>На обратный путь по течению затрачено меньше времени, поэтому:</p>"
        html += line(term_up + "-" + term_down + "=" + n(q.durations["delay"].total))
    elif q.kind == "water_raft":
        html += "<p>Время рейса яхты с учётом задержки старта равно времени движения плота:</p>"
        html += line(
            term_down
            + "+"
            + term_up
            + "+"
            + n(q.durations["delay"].total)
            + "="
            + frac(n(v["raft_distance"]), n(v["known"]))
        )
    else:
        html += "<p>Время движения складывается из времени прохождения одинакового расстояния по течению и против течения:</p>"
        html += line(term_up + "+" + term_down + "=" + n(q.durations["moving"].total))
    if q.kind in {"water_boat_difference", "water_current_stay", "water_current_clock"}:
        return html + square_steps(a)
    if q.kind == "water_current_difference":
        return html + cleared_equation(a) + even_steps(a, note=True)
    html += quadratic_steps(a)
    if q.kind == "water_boat_stay":
        html += vieta(a)
    if q.kind == "water_raft":
        html += "<p><b>Примечание.</b> Вычисления можно упростить формулой для чётного коэффициента при неизвестной:</p>"
        html += even_steps(a) + square_completion(a)
    return html


def ordinary(a):
    q, v = a.question, a.question.values
    gap, distance = n(v["gap"]), n(v["distance"])
    html = conversions(q)
    if q.kind == "water_follow":
        role = "второго" if q.target_fast else "первого"
        html += f"<p>Пусть u км/ч — скорость {role} теплохода. Скорость другого теплохода равна:</p>"
        html += line("u" + ("-" if q.target_fast else "+") + gap)
        html += "<p>Первый теплоход вышел раньше, но оба прибыли одновременно. Разность времён движения равна задержке старта:</p>"
    elif q.kind == "water_lake_return":
        route = "В в А" if q.target_fast else "А в В"
        html += f"<p>Пусть u км/ч — скорость баржи на пути из {route}. Скорость на другом пути равна:</p>"
        html += line("u" + ("-" if q.target_fast else "+") + gap)
        html += "<p>Остановка на обратном пути уравняла полное время обратного и прямого пути:</p>"
    else:
        html += "<p>Пусть u км/ч — скорость старого катера, тогда скорость катера на подводных крыльях равна:</p>"
        html += line("u+" + gap)
        html += (
            "<p>Новый катер проходит то же расстояние быстрее на указанное время:</p>"
        )
    html += line("u>" + (gap if q.target_fast else "0"))
    delay = n(q.durations["delay"].total)
    if q.target_fast:
        equation = frac(distance, "u-" + gap) + "-" + frac(distance, "u") + "=" + delay
    else:
        equation = frac(distance, "u") + "-" + frac(distance, "u+" + gap) + "=" + delay
    return html + line(equation) + quadratic_steps(a)


def distance(a):
    q, v = a.question, a.question.values
    up, down = v["boat"] - v["current"], v["boat"] + v["current"]
    moving = q.durations["moving"].total
    html = "<p>Пусть весь путь теплохода равен 2S км. Найдём скорости против течения и по течению:</p>"
    html += line(
        r"v_{\mathrm{против}}=" + n(v["boat"]) + "-" + n(v["current"]) + "=" + n(up)
    )
    html += line(
        r"v_{\mathrm{по}}=" + n(v["boat"]) + "+" + n(v["current"]) + "=" + n(down)
    )
    html += time_budget(q)
    html += "<p>Сумма времён прохождения двух одинаковых участков равна времени движения:</p>"
    html += line(frac("S", n(up)) + "+" + frac("S", n(down)) + "=" + n(moving))
    coefficient = 1 / up + 1 / down
    html += line(n(coefficient) + "S=" + n(moving))
    html += line("S=" + n(a.root))
    return (
        html
        + "<p>В условии требуется весь путь туда и обратно:</p>"
        + line("2S=2\\cdot" + n(a.root) + "=" + n(a.result))
    )


def proof(a):
    kind = a.question.kind
    if kind in {"water_follow", "water_lake_return", "water_upgrade"}:
        return ordinary(a)
    if kind == "water_distance":
        return distance(a)
    if kind in {"water_season_current", "water_season_boat"}:
        from .water_season_proof import proof as season

        return season(a)
    return stream(a)
