"""Parent methods: elapsed-time equations, physical roots and harmonic mean."""

import sympy as sp

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_models import X


def half_setup(q):
    known, gap = map(n, (q.values["known"], q.values["gap"]))
    sign = "+" if q.kind == "half_gain" else "-"
    part = "второй" if sign == "+" else "первой"
    total = "1" if sign == "+" else "2"
    html = f"<p>Пусть v км/ч — скорость первого автомобиля, тогда скорость второго автомобиля на {part} половине пути равна:</p>"
    html += line("v" + sign + gap)
    html += f"<p>Примем расстояние между пунктами за {total}. Автомобили были в пути одно и то же время, откуда имеем:</p>"
    if sign == "+":
        equation = (
            frac("1", "v")
            + "="
            + frac("0{,}5", known)
            + "+"
            + frac("0{,}5", "v+" + gap)
        )
    else:
        equation = frac("2", "v") + "=" + frac("1", known) + "+" + frac("1", "v-" + gap)
    return html, equation


def speed_setup(q):
    gap, distance = n(q.values["gap"]), n(q.values["distance"])
    delay = n(q.durations["delay"].total)
    sign = "-" if q.target_fast else "+"
    if q.kind == "later":
        html = "<p>Пусть v км/ч — скорость велосипедиста, тогда скорость автомобилиста равна:</p>"
        explanation = "Велосипедист был в пути на указанное время больше автомобилиста. Используем формулу времени t=S/v:"
    elif q.kind == "race":
        place = "первым" if q.target_fast else "вторым"
        other = "вторым" if q.target_fast else "первым"
        html = f"<p>Пусть v км/ч — скорость {q.actor}, пришедшего к финишу {place}, тогда скорость {q.actor}, пришедшего {other}, равна:</p>"
        explanation = "Первый участник прибыл к финишу раньше второго. Разность времени прохождения одного и того же расстояния равна указанному времени:"
    else:
        route = "В в А" if q.target_fast else "А в В"
        other = "А в В" if q.target_fast else "В в А"
        html = f"<p>Пусть v км/ч — скорость велосипедиста на пути из {route}, тогда скорость на пути из {other} равна:</p>"
        explanation = "Сделав на обратном пути остановку, велосипедист затратил на обратный путь столько же времени, сколько на путь из А в В:"
    html += line("v" + sign + gap) + "<p>" + explanation + "</p>"
    if q.kind == "later":
        equation = frac(distance, "v") + "-" + frac(distance, "v+" + gap) + "=" + delay
    elif q.target_fast:
        equation = frac(distance, "v") + "+" + delay + "=" + frac(distance, "v-" + gap)
    else:
        equation = frac(distance, "v") + "=" + frac(distance, "v+" + gap) + "+" + delay
    return html, equation


def trip_setup(q):
    delay = n(q.durations["delay"].total)
    meet = n(q.durations["meeting"].total)
    html = "<p>Примем расстояние между городами за 1. Пусть время движения велосипедиста равно x ч, тогда время движения мотоциклиста равно:</p>"
    html += line("x-" + delay)
    html += "<p>Их скорости равны обратным величинам полного времени пути. К моменту встречи они в сумме преодолели всё расстояние между городами:</p>"
    return html, r"\left(" + frac("1", "x") + "+" + frac(
        "1", "x-" + delay
    ) + r"\right)\cdot" + meet + "=1"


def conversions(q):
    html = ""
    for key, duration in q.durations.items():
        if duration.minutes:
            purpose = {
                "meeting": "Время до встречи",
                "total": "Всё время пути",
                "down": "Время спуска",
                "lap_time": "Время до первого обгона",
                "stop": "Время стоянки",
                "elapsed": "Всё время рейса",
            }.get(key, "Указанное время")
            html += f"<p>{purpose} переведём в часы:</p>"
            html += line(
                n(duration.hours)
                + "+"
                + frac(n(duration.minutes), "60")
                + "="
                + n(duration.total)
            )
    return html


def quadratic_steps(a):
    symbol = a.question.symbol
    poly = sp.Poly(a.polynomial, X)
    c2, c1, c0 = (poly.nth(i) for i in (2, 1, 0))
    disc = c1**2 - 4 * c2 * c0
    html = "<p>При указанных ограничениях знаменатели не равны нулю. Умножим уравнение на общий знаменатель и приведём подобные слагаемые:</p>"
    denominator = sp.together(a.balance.left - a.balance.right).as_numer_denom()[1]
    left, right = (
        sp.cancel(side * denominator) for side in (a.balance.left, a.balance.right)
    )
    html += line(
        sp.latex(left, symbol_names={X: symbol})
        + "="
        + sp.latex(right, symbol_names={X: symbol})
    )
    html += line(sp.latex(a.polynomial, symbol_names={X: symbol}) + "=0")
    html += line(
        "D=(" + n(c1) + ")^2-4\\cdot(" + n(c2) + ")\\cdot(" + n(c0) + ")=" + n(disc)
    )
    html += line(
        symbol
        + "="
        + frac("-(" + n(c1) + r")\pm\sqrt{" + n(disc) + "}", "2\\cdot(" + n(c2) + ")")
    )
    html += line(symbol + r"\in\left\{" + ";".join(n(r) for r in a.roots) + r"\right\}")
    html += "<p>Выберем корень, удовлетворяющий ограничениям условия и положительности времени и скоростей:</p>"
    return html + line(symbol + "=" + n(a.root))


def harmonic_note(a):
    q = a.question
    first, second = a.root - q.values["gap"], q.values["known"]
    html = "<p><b>Примечание.</b> Оба автомобиля проехали одинаковое расстояние за одно и то же время, значит, средние скорости их движения равны. Скорости второго автомобиля на половинах пути равны:</p>"
    html += line(
        n(a.root) + "-" + n(q.values["gap"]) + "=" + n(first) + r",\quad " + n(second)
    )
    if first != second:
        html += line(frac(n(first) + "+" + n(second), "2") + r"\ne " + n(a.root))
        html += "<p>Противоречия нет: на половину пути с меньшей скоростью затрачено больше времени. Поэтому среднюю скорость нельзя находить как среднее арифметическое. Пусть каждая половина пути равна z км. Время прохождения каждой половины и средняя скорость равны:</p>"
    else:
        html += "<p>В этом случае скорости на обеих половинах совпали. В общем случае равные пути проходят за разное время. Пусть каждая половина пути равна z км:</p>"
    html += line("t_1=" + frac("z", n(first)) + r",\quad t_2=" + frac("z", n(second)))
    html += line(
        r"v_{\mathrm{ср}}="
        + frac("2z", frac("z", n(first)) + "+" + frac("z", n(second)))
        + "="
        + frac("2\\cdot" + n(first) + r"\cdot" + n(second), n(first) + "+" + n(second))
        + "="
        + n(a.root)
    )
    return (
        html
        + "<p>Средняя скорость второго автомобиля действительно равна скорости первого.</p>"
    )


def delayed_point_proof(a):
    q, v = a.question, a.question.values
    distance = n(v["distance"])
    delay = n(q.durations["delay"].total)
    first, second = n(v["first"]), n(v["second"])
    html = "<p>Пусть автомобили встретятся на расстоянии S км от города А, тогда второй автомобиль пройдёт расстояние:</p>"
    html += (
        line(distance + "-S")
        + "<p>Второй автомобиль находился в пути на указанное время меньше первого:</p>"
    )
    html += line(frac("S", first) + "=" + frac(distance + "-S", second) + "+" + delay)
    html += line(
        second
        + "S="
        + first
        + r"\left("
        + distance
        + "-S+"
        + second
        + r"\cdot"
        + delay
        + r"\right)"
    )
    rhs = v["first"] * (v["distance"] + v["second"] * q.durations["delay"].total)
    html += line(n(v["first"] + v["second"]) + "S=" + n(rhs))
    return html + line("S=" + n(a.result))


def linear_proof(a):
    q, v = a.question, a.question.values
    distance = n(v["distance"])
    if q.kind == "meeting":
        first, second = n(v["first"]), n(v["second"])
        html = "<p>Пусть t ч — время движения автомобилей до встречи. До встречи они в сумме проедут всё расстояние между городами:</p>"
        return (
            html
            + line(first + "t+" + second + "t=" + distance)
            + line(n(v["first"] + v["second"]) + "t=" + distance)
            + line(
                "t=" + frac(distance, n(v["first"] + v["second"])) + "=" + n(a.result)
            )
        )
    delay = n(q.durations["delay"].total)
    point = n(v["point"])
    remaining = n(v["distance"] - v["point"])
    if q.kind == "meeting_point":
        html = "<p>Автомобиль, выехавший из города А, преодолел расстояние:</p>"
        html += line(distance + "-" + point + "=" + remaining)
        return (
            html
            + "<p>Разделим пройденное расстояние на время до встречи:</p>"
            + line("v=" + frac(remaining, delay) + "=" + n(a.result))
        )
    html = "<p>Пусть v км/ч — скорость первого автомобиля. Второй автомобиль преодолел расстояние:</p>"
    html += line(distance + "-" + point + "=" + remaining)
    html += (
        "<p>Первый автомобиль находился в пути на указанное время больше второго:</p>"
    )
    total = q.durations["delay"].total + (v["distance"] - v["point"]) / v["second"]
    html += line(
        frac(point, "v")
        + "="
        + delay
        + "+"
        + frac(remaining, n(v["second"]))
        + "="
        + n(total)
    )
    return html + line("v=" + frac(point, n(total)) + "=" + n(a.result))


def proof(a):
    from .motion_extended_proof import PROOFS

    q = a.question
    if q.kind.startswith("water_"):
        from .water_proof import proof as water

        return water(a)
    if q.kind in PROOFS:
        return PROOFS[q.kind](a)
    html = conversions(q)
    if q.kind in {"meeting", "meeting_point", "delayed_point", "delayed_speed"}:
        return html + (
            delayed_point_proof(a) if q.kind == "delayed_point" else linear_proof(a)
        )
    if q.kind in {"half_gain", "half_loss"}:
        setup, equation = half_setup(q)
    elif q.kind == "trip_time":
        setup, equation = trip_setup(q)
    else:
        setup, equation = speed_setup(q)
    html += setup
    domain = a.balance.domain
    html += line(q.symbol + ">" + n(domain.start))
    if q.kind == "half_loss":
        html += "<p>Учтём указанную нижнюю границу скорости и положительность скорости на первой половине пути.</p>"
    html += line(equation) + quadratic_steps(a)
    return html + (harmonic_note(a) if q.kind == "half_loss" else "")
