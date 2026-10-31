"""Equal test sizes and whole hourly task counts with exact time equations."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_proof import quadratic_steps
from .work_sum_proof import conversions


def test_count(a):
    v = a.question.values
    first, second = v["names"]
    html = conversions(a.question)
    html += f"<p>Пусть N — число вопросов в тесте, N — положительное целое число. {first} отвечает на вопросы медленнее, чем {second}. Время каждого равно числу вопросов, делённому на число ответов за час:</p>"
    html += line(
        "t_1=" + frac("N", n(v["rate1"])) + r",\quad t_2=" + frac("N", n(v["rate2"]))
    )
    html += "<p>Первый участник закончил позже второго. Составим уравнение разности времён:</p>"
    html += line(
        frac("N", n(v["rate1"])) + "-" + frac("N", n(v["rate2"])) + "=" + n(v["delay"])
    )
    html += line(
        "N="
        + frac(n(v["delay"]), frac("1", n(v["rate1"])) + "-" + frac("1", n(v["rate2"])))
        + "="
        + n(a.result)
    )
    return html + "<p>Получено положительное целое число вопросов, как и требуется.</p>"


def integer_solver(a):
    v = a.question.values
    fast, slow = v["names"]
    html = conversions(a.question)
    html += f"<p>Пусть {slow} решает n задач в час. По условию n — положительное целое число. Тогда {fast} решает на указанное число задач больше, а вместе они складывают свои производительности:</p>"
    html += line(
        r"n\in\mathbb{Z},\quad n>0,\quad v_{\mathrm{быстрого}}=n+"
        + n(v["gap"])
        + r",\quad v_{\mathrm{вместе}}=2n+"
        + n(v["gap"])
    )
    html += "<p>При совместной работе тот же объём задач будет выполнен быстрее, чем первым участником в одиночку. Разность времён равна:</p>"
    html += line(
        frac(n(v["joint_tasks"]), "n+" + n(v["gap"]))
        + "-"
        + frac(n(v["joint_tasks"]), "2n+" + n(v["gap"]))
        + "="
        + n(v["delay"])
    )
    html += quadratic_steps(a, quantities="времени и производительностей")
    rejected = [root for root in a.roots if root != a.root]
    html += "<p>Учитываем целочисленность числа задач за час. Остальные корни не удовлетворяют этому условию или положительности:</p>"
    if rejected:
        html += line(r"n\ne " + r",\quad n\ne ".join(map(n, rejected)))
    html += f"<p>Найдём, за сколько часов {slow} решит требуемое число задач:</p>"
    return html + line("t=" + frac(n(v["target"]), n(a.root)) + "=" + n(a.result))
