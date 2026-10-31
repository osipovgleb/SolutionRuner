"""The same relative displacement applied to laps and opposite starting points."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section


def opposite_points(a):
    v = a.question.values
    hours = a.result / 60
    html = "<p>Пусть v км/ч — скорость первого мотоциклиста, тогда скорость второго равна:</p>"
    html += line("v+" + n(a.rate))
    html += "<p>Чтобы поравняться в первый раз, более быстрый должен преодолеть начальное расстояние между ними, равное половине длины трассы. Пусть это произойдёт через t часов:</p>"
    html += line("d=" + frac(n(v["distance"]), "2") + "=" + n(a.displacement))
    html += line("(v+" + n(a.rate) + ")t-vt=" + n(a.displacement))
    html += line(n(a.rate) + "t=" + n(a.displacement))
    html += line("t=" + n(hours) + r"\,\mathrm{ч}=" + n(a.result) + r"\,\mathrm{мин}")
    other = "<p>Быстрый мотоциклист движется относительно медленного со скоростью, равной разности их скоростей. Разделим половину длины трассы на эту скорость:</p>"
    other += line(
        "t=" + frac(n(a.displacement), n(a.rate)) + "=" + n(hours) + r"\,\mathrm{ч}"
    )
    other += line("60\\cdot(" + n(hours) + ")=" + n(a.result) + r"\,\mathrm{мин}")
    return section(html, "Решение") + section(other, "Приведём другое решение")


def lap_speed(a):
    v = a.question.values
    hours = a.question.time.total_seconds / 3600
    html = "<p>Пусть скорость второго автомобиля равна v км/ч. Переведём указанное время в часы:</p>"
    conversion = frac(n(a.question.time.minutes), "60")
    if a.question.time.seconds:
        conversion += "+" + frac(n(a.question.time.seconds), "3600")
    html += line("t=" + conversion + "=" + n(hours))
    html += "<p>Первый автомобиль прошёл за это время на один круг больше второго:</p>"
    html += line(
        n(v["first"])
        + r"\cdot("
        + n(hours)
        + ")=v\\cdot("
        + n(hours)
        + ")+"
        + n(v["distance"])
    )
    html += line(
        "v\\cdot(" + n(hours) + ")=" + n(v["first"] * hours) + "-" + n(v["distance"])
    )
    return html + line(
        "v="
        + n(v["first"])
        + "-"
        + frac(n(v["distance"]), n(hours))
        + "="
        + n(a.result)
    )


def lap_chase(a):
    v = a.question.values
    lag, catch, lap = (v[k] for k in ("lag_minutes", "catch_minutes", "lap_minutes"))
    ratio = (lag + catch) / catch
    bicycle = a.result - a.rate
    html = "<p>К моменту первого обгона мотоциклист прошёл столько же, сколько велосипедист за время от его выезда. Поэтому отношение их скоростей равно обратному отношению времён:</p>"
    html += line(
        frac("v_{\\mathrm{м}}", "v_{\\mathrm{в}}")
        + "="
        + frac(n(lag + catch), n(catch))
        + "="
        + n(ratio)
    )
    html += "<p>Пусть x км/ч — скорость велосипедиста, тогда скорость мотоциклиста и скорость их сближения равны:</p>"
    html += line(r"v_{\mathrm{м}}=" + n(ratio) + r"x,\quad u=(" + n(ratio) + "-1)x")
    html += "<p>Между первым и вторым обгоном мотоциклист проехал на один круг больше. Найдём скорость сближения:</p>"
    html += line("t=" + frac(n(lap), "60") + "=" + n(lap / 60))
    html += line("u=" + frac(n(v["distance"]), n(lap / 60)) + "=" + n(a.rate))
    html += line(
        "(" + n(ratio) + "-1)x=" + n(a.rate) + r"\quad\Rightarrow\quad x=" + n(bicycle)
    )
    return html + line(
        r"v_{\mathrm{м}}=" + n(ratio) + r"\cdot" + n(bicycle) + "=" + n(a.result)
    )


PROOFS = {
    "opposite_points": opposite_points,
    "lap_speed": lap_speed,
    "lap_chase": lap_chase,
}
