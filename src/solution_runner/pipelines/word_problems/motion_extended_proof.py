"""Elapsed-time proofs for converted rates, slopes and stopped arrivals."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import catch_return, third_cyclist
from .motion_proof import conversions, quadratic_steps
from .motion_walk_proof import proof as walk_return


def freight(a):
    q, v = a.question, a.question.values
    html = "<p>Скорость товарного поезда меньше скорости скорого на указанное число метров в минуту. Переведём эту разность в километры в час:</p>"
    html += line(
        frac(n(v["metres_per_minute"] / 1000), frac("1", "60"))
        + "="
        + n(v["gap"])
        + r"\,\mathrm{км}/\mathrm{ч}"
    )
    html += (
        "<p>Пусть v км/ч — скорость товарного поезда, тогда скорость скорого равна:</p>"
    )
    html += line("v+" + n(v["gap"])) + line("v>0")
    html += conversions(q)
    html += "<p>Товарный поезд тратит на тот же путь больше времени, поэтому:</p>"
    html += line(
        frac(n(v["distance"]), "v")
        + "="
        + frac(n(v["distance"]), "v+" + n(v["gap"]))
        + "+"
        + n(q.durations["delay"].total)
    )
    return html + quadratic_steps(a)


def midpoint(a):
    q, v = a.question, a.question.values
    half = v["distance"] / 2
    html = "<p>Поезда встретились на середине пути, поэтому каждый прошёл половину расстояния между городами:</p>"
    html += line("S=" + frac(n(v["distance"]), "2") + "=" + n(half))
    html += (
        "<p>Пусть x км/ч — скорость первого поезда, тогда скорость второго равна:</p>"
    )
    html += line("x+" + n(v["gap"])) + line("x>0")
    html += "<p>Второй поезд вышел позже первого, значит, время движения первого больше на указанную задержку:</p>"
    html += line(
        frac(n(half), "x")
        + "="
        + frac(n(half), "x+" + n(v["gap"]))
        + "+"
        + n(q.durations["delay"].total)
    )
    html += quadratic_steps(a)
    return (
        html
        + "<p>Найдём запрошенную скорость второго поезда:</p>"
        + line("v_2=" + n(a.root) + "+" + n(v["gap"]) + "=" + n(a.result))
    )


def downhill(a):
    q, v = a.question, a.question.values
    total, down = (q.durations[key].total for key in ("total", "down"))
    up = total - down
    html = conversions(q)
    html += "<p>Пусть x км/ч — скорость туриста на спуске. На подъёме он движется медленнее:</p>"
    html += line("v_{\\mathrm{под}}=x-" + n(v["gap"]) + ">0")
    html += line("t_{\\mathrm{под}}=" + n(total) + "-" + n(down) + "=" + n(up))
    html += "<p>Длина каждого участка равна произведению скорости на время. Сумма длин подъёма и спуска равна всей длине дороги:</p>"
    html += line(
        "S_{\\mathrm{сп}}="
        + n(down)
        + r"\cdot x,\quad S_{\mathrm{под}}="
        + n(up)
        + "(x-"
        + n(v["gap"])
        + ")"
    )
    html += line(n(down) + "x+" + n(up) + "(x-" + n(v["gap"]) + ")=" + n(v["distance"]))
    rhs = v["distance"] + up * v["gap"]
    html += line(
        n(total)
        + "x="
        + n(v["distance"])
        + "+"
        + n(up)
        + r"\cdot"
        + n(v["gap"])
        + "="
        + n(rhs)
    )
    return html + line("x=" + frac(n(rhs), n(total)) + "=" + n(a.result))


def mixed_hours(value):
    if (60 * value).is_Integer is not True:
        return ""
    hours = value // 1
    minutes = 60 * (value - hours)
    return "=" + n(hours) + r"\,\mathrm{ч}\;" + n(minutes) + r"\,\mathrm{мин}"


def stopped(a):
    q, v = a.question, a.question.values
    total = v["reference_distance"] / v["known"]
    delay = q.durations["delay"].total
    moving = total - delay
    known, rider = (
        ("Алексей", "Иван")
        if q.kind == "named_stop"
        else ("Автомобилист", "Мотоциклист")
    )
    html = f"<p>{known} приедет в пункт назначения через:</p>"
    html += line(
        "T="
        + frac(n(v["reference_distance"]), n(v["known"]))
        + "="
        + n(total)
        + mixed_hours(total)
    )
    html += conversions(q)
    html += f"<p>Обозначим искомую скорость через v км/ч. {rider} должен прибыть одновременно с ним; время остановки входит в общее время пути:</p>"
    html += line(frac(n(v["distance"]), "v") + "+" + n(delay) + "=" + n(total))
    html += "<p>Вычтем время остановки, чтобы найти время движения:</p>"
    html += line(
        "t=" + n(total) + "-" + n(delay) + "=" + n(moving) + mixed_hours(moving)
    )
    return html + line("v=" + frac(n(v["distance"]), n(moving)) + "=" + n(a.result))


PROOFS = {
    "freight": freight,
    "midpoint": midpoint,
    "downhill": downhill,
    "stopped": stopped,
    "named_stop": stopped,
    "catch_return": catch_return,
    "third_cyclist": third_cyclist,
    "walk_return": walk_return,
}
