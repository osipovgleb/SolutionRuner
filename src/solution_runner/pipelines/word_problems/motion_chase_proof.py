"""Both parent methods for catching a car or two earlier cyclists."""

from ..probability.common import line
from .common import UnsupportedCondition
from .math_common import fraction as frac
from .math_common import number as n
from .motion_models import alternate
from .motion_proof import conversions, quadratic_steps


def section(html, title):
    return f'<section data-content-kind="solution" data-solution-title="{title}">{html}</section>'


def catch_time_method(a):
    q, v = a.question, a.question.values
    delay, speed, distance = (
        n(q.durations["delay"].total),
        n(v["known"]),
        n(v["distance"]),
    )
    html = conversions(q)
    html += "<p>Обозначим S км — расстояние от А до С, v км/ч — скорость автомобиля, t ч — время движения мотоциклиста от А до С. До встречи и до возвращения мотоциклиста в А получаем:</p>"
    html += line(
        r"\begin{cases}(t+"
        + delay
        + ")v="
        + speed
        + r"t,\\(2t+"
        + delay
        + ")v="
        + distance
        + r".\end{cases}"
    )
    html += "<p>Разделим первое уравнение на второе. Скорость автомобиля положительна, поэтому её можно сократить:</p>"
    html += line(frac("t+" + delay, "2t+" + delay) + "=" + frac(speed + "t", distance))
    html += line("t>0") + quadratic_steps(a)
    car_speed = v["distance"] / (2 * a.root + q.durations["delay"].total)
    html += line(
        "v="
        + frac(distance, "2\\cdot(" + n(a.root) + ")+" + delay)
        + "="
        + n(car_speed)
    )
    return html + line("S=" + speed + r"\cdot(" + n(a.root) + ")=" + n(a.result))


def catch_speed_method(a):
    q, v = a.question, a.question.values
    delay, speed, distance = (
        n(q.durations["delay"].total),
        n(v["known"]),
        n(v["distance"]),
    )
    html = "<p>Обозначим v км/ч — скорость автомобиля. В момент выезда мотоциклиста автомобиль уже прошёл расстояние:</p>"
    html += line(delay + "v") + line("0<v<" + speed)
    html += "<p>Мотоциклист догонит автомобиль за время, равное начальному отрыву, делённому на скорость сближения. На возвращение он потратит столько же времени:</p>"
    html += line("t=" + frac(delay + "v", speed + "-v"))
    html += "<p>Всё это время автомобиль движется с постоянной скоростью. Его полный путь равен расстоянию между городами:</p>"
    html += line(
        r"\left(2\cdot"
        + frac(delay + "v", speed + "-v")
        + "+"
        + delay
        + r"\right)v="
        + distance
    )
    html += quadratic_steps(a)
    time = q.durations["delay"].total * a.root / (v["known"] - a.root)
    html += line(
        "t="
        + frac(delay + r"\cdot" + n(a.root), speed + "-" + n(a.root))
        + "="
        + n(time)
    )
    return html + line("S=" + speed + r"\cdot(" + n(time) + ")=" + n(a.result))


def catch_return(a):
    other = alternate(a.question)
    if a.result != other.result:
        raise UnsupportedCondition(
            "both catch-and-return methods must give the same distance"
        )
    return section(catch_time_method(a), "Решение") + section(
        catch_speed_method(other), "Приведём другой способ решения"
    )


def third_time_method(a):
    q, v = a.question, a.question.values
    first, second, delay = n(v["first"]), n(v["second"]), n(q.durations["delay"].total)
    html = conversions(q)
    html += "<p>Пусть v км/ч — скорость третьего велосипедиста, а t ч — время, которое понадобилось ему, чтобы догнать второго. Второй выехал на час раньше третьего:</p>"
    html += line("vt=" + second + "(t+1)")
    html += line("v=" + frac(second + "(t+1)", "t"))
    html += "<p>Когда третий догнал первого, первый находился в пути на два часа дольше третьего:</p>"
    html += line("v(t+" + delay + ")=" + first + "(t+" + delay + "+2)")
    html += "<p>Подставим выражение скорости через время:</p>"
    html += line(
        frac(second + "(t+1)", "t")
        + "(t+"
        + delay
        + ")="
        + first
        + "(t+"
        + delay
        + "+2)"
    )
    html += line("t>0") + quadratic_steps(a)
    return html + line(
        "v=" + frac(second + "(" + n(a.root) + "+1)", n(a.root)) + "=" + n(a.result)
    )


def third_speed_method(a):
    q, v = a.question, a.question.values
    first, second, delay = n(v["first"]), n(v["second"]), n(q.durations["delay"].total)
    html = "<p>Примем за x км/ч скорость третьего велосипедиста. Скорости сближения со вторым и первым равны:</p>"
    html += line("x-" + second + r",\quad x-" + first)
    html += line("x>" + n(max(v["first"], v["second"])))
    html += "<p>Второй выехал на час раньше третьего, а первый — на два часа. Чтобы преодолеть начальные отрывы, третьему требуется время:</p>"
    html += line(
        "t_2="
        + frac(second, "x-" + second)
        + r",\quad t_1="
        + frac(n(2 * v["first"]), "x-" + first)
    )
    html += "<p>Первого он догнал на указанное время позже второго, поэтому:</p>"
    html += line(
        frac(second, "x-" + second)
        + "+"
        + delay
        + "="
        + frac(n(2 * v["first"]), "x-" + first)
    )
    return html + quadratic_steps(a)


def third_cyclist(a):
    other = alternate(a.question)
    if a.result != other.result:
        raise UnsupportedCondition(
            "both three-cyclist methods must give the same speed"
        )
    return section(third_time_method(a), "Решение") + section(
        third_speed_method(other), "Приведем другое решение."
    )
