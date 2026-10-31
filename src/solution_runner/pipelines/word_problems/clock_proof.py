"""Five parent clock methods, corrected arithmetic and the general theorem."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section


def hour_divisions(a, markup):
    q = a.question
    arc, turns = a.angle / 30, 12 * (q.count - 1)
    total = arc + turns
    hours = a.result / 60
    html = "<p>До искомой встречи минутная стрелка должна сначала пройти разделяющее стрелки расстояние в направлении своего движения, затем обойти полный круг для каждой следующей встречи и пройти ещё L часовых делений, на которые за это время повернётся часовая стрелка:</p>"
    html += line(
        "d=" + n(arc) + r",\quad 12(n-1)=12\cdot" + str(q.count - 1) + "=" + str(turns)
    )
    html += "<p>Скорость минутной стрелки в 12 раз больше часовой. Приравняем времена их движения:</p>"
    html += line(frac("L", "1") + "=" + frac(n(arc) + "+" + str(turns) + "+L", "12"))
    html += line("12L=L+" + n(total))
    html += line("11L=" + n(total) + r"\quad\Rightarrow\quad L=" + n(hours))
    html += line("t=60\\cdot(" + n(hours) + ")=" + n(a.result) + r"\,\mathrm{мин}")
    if markup:
        html += "<p>На рисунке показано исходное положение стрелок; до 12-часового деления минутной стрелке остаётся 5 часовых делений, а часовая уже прошла 1 и 35/60 деления:</p>"
        html += line("d=5+1+" + frac("35", "60") + "=" + n(arc))
        html += markup
    return html


def arithmetic(a):
    q = a.question
    circles = a.angle / 360
    total = circles + q.count - 1
    html = "<p>Скорость минутной стрелки — 1 круг в час, часовой — 1/12 круга в час. Скорость сближения равна:</p>"
    html += line("u=1-" + frac("1", "12") + "=" + frac("11", "12"))
    html += "<p>Начальное расстояние по окружности и дополнительные полные круги дают общий относительный путь. Разделим его на скорость сближения:</p>"
    html += line("S=" + n(circles) + "+" + str(q.count - 1) + "=" + n(total))
    html += line(
        "t="
        + frac(n(total), frac("11", "12"))
        + "="
        + n(a.result / 60)
        + r"\,\mathrm{ч}"
    )
    return html + line(
        "60\\cdot(" + n(a.result / 60) + ")=" + n(a.result) + r"\,\mathrm{мин}"
    )


def short(a):
    q = a.question
    current = 60 * q.hour + q.minute
    passed = 11 * current // 720
    target = passed + q.count
    html = "<p>За 12 часов минутная стрелка опережает часовую на 11 полных кругов, поэтому после совпадения в 12 часов следуют 11 встреч до следующего совпадения в 12 часов:</p>"
    html += line(r"t_k=\frac{720k}{11},\quad k=1,2,\ldots,11")
    html += "<p>Посчитаем, сколько встреч уже прошло после 12 часов, и номер искомой встречи в этой последовательности:</p>"
    html += line(
        "k_0="
        + r"\left\lfloor"
        + frac("11\\cdot" + str(current), "720")
        + r"\right\rfloor="
        + str(passed)
    )
    html += line("k=" + str(passed) + "+" + str(q.count) + "=" + str(target))
    if target % 11 == 0:
        hour = 12 * (target // 11)
        html += f"<p>Это совпадение в {hour} часов ровно. Вычтем исходное время:</p>"
        return html + line(
            "t="
            + str(60 * hour)
            + "-(60\\cdot"
            + str(q.hour)
            + "+"
            + str(q.minute)
            + ")="
            + n(a.result)
            + r"\,\mathrm{мин}"
        )
    return html + line(
        "t="
        + frac("720\\cdot" + str(target), "11")
        + "-"
        + str(current)
        + "="
        + n(a.result)
    )


def progression(a):
    q = a.question
    first_arc = a.angle / 6
    html = "<p>Минутная стрелка движется в 12 раз быстрее часовой. Пока она проходит начальное расстояние в минутных делениях, часовая отдаляется на 1/12 этого расстояния. Затем остаётся ещё в 12 раз меньший промежуток. Получаем бесконечно убывающую геометрическую прогрессию:</p>"
    html += line("b_1=" + n(first_arc) + r",\quad q=\frac{1}{12}")
    html += line(
        "S_1="
        + frac("b_1", "1-q")
        + "="
        + frac(n(first_arc), frac("11", "12"))
        + "="
        + n(a.first)
    )
    html += "<p>От одной встречи до следующей нужно преодолеть полный круг из 60 минутных делений. Для каждой следующей встречи используем ту же прогрессию:</p>"
    html += line(
        "b'_1=60,\\quad S_2=" + frac("60", frac("11", "12")) + "=" + n(a.interval)
    )
    html += line(
        "S="
        + n(a.first)
        + "+"
        + str(q.count - 1)
        + r"\cdot"
        + n(a.interval)
        + "="
        + n(a.result)
    )
    html += "<p><b>Примечание.</b> Если бы изначально на часах было, к примеру, 8 часов 20 минут, минутная стрелка прошла бы от 12-го деления 20 минутных делений, а часовая сдвинулась бы от 8-го часового деления ещё на 20/12 минутного деления. Этот пример поясняет выбор первого члена прогрессии:</p>"
    return html + line(
        "b_1=40+"
        + frac("20", "12")
        + "-20=20+"
        + frac("20", "12")
        + "="
        + frac("65", "3")
    )


def general(a):
    q = a.question
    html = "<p>Скорость вращения часовой стрелки равна 0,5 градуса в минуту, минутной — 6 градусов в минуту. Когда часы показывают h часов m минут, углы относительно 12-часового деления равны:</p>"
    html += line(r"\alpha=30h+0{,}5m,\quad\beta=6m")
    html += "<p>Если минутная ещё не прошла положение часовой, при первой встрече углы сравняются. Если уже прошла — минутная должна дополнительно пройти полный круг. В случае исходного совпадения считаем первую будущую встречу:</p>"
    html += line(r"6m+6t_1=30h+0{,}5m+0{,}5t_1+360j")
    html += line(
        r"t_1=\frac{60h-11m+720j}{11},\quad j=\begin{cases}0,&60h-11m>0,\\1,&60h-11m\le0.\end{cases}"
    )
    html += line(r"0{,}5t_2=6t_2-360\quad\Rightarrow\quad t_2=\frac{720}{11}")
    html += "<p>Для встречи с номером n добавим n−1 одинаковых промежутков между встречами:</p>"
    html += line(r"t_n=\frac{60h-11m+720j+720(n-1)}{11}")
    branch = 0 if 60 * q.hour - 11 * q.minute > 0 else 1
    html += line(
        "h="
        + str(q.hour)
        + ",\\quad m="
        + str(q.minute)
        + ",\\quad n="
        + str(q.count)
        + ",\\quad j="
        + str(branch)
    )
    return html + line(
        "t_n="
        + frac(
            str(60 * q.hour - 11 * q.minute)
            + "+720\\cdot"
            + str(branch)
            + "+720\\cdot"
            + str(q.count - 1),
            "11",
        )
        + "="
        + n(a.result)
    )


def proof(a, markup=""):
    return (
        section(hour_divisions(a, markup), "Решение")
        + section(arithmetic(a), "Приведем арифметическое решение.")
        + section(short(a), "Приведем короткое решение.")
        + section(
            progression(a),
            "Решение при помощи геометрической прогрессии (Эмиль Бахшинян)",
        )
        + section(general(a), "Приведем решение в общем виде.")
    )
