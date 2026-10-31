"""Parent arithmetic-progression reasoning, adapted to its requested member."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n


def introduction(q):
    subject, unit = {
        "fence": ("бригада покрасила", "метров забора"),
        "snail": ("улитка проползла", "метров"),
        "tunnel": ("рабочие проложили", "метров тоннеля"),
        "tasks": (q.name + " решил", "задач"),
        "tourist": ("турист прошёл", "километров"),
        "truck": ("грузовик перевёз", "тонн щебня"),
        "cards": (q.name + " подписала", "открыток"),
    }[q.kind]
    return f"<p>Пусть в первый день {subject} a₁ {unit}, во второй — a₂, …, в последний — aₙ. Ежедневная прибавка одна и та же, поэтому эти величины образуют арифметическую прогрессию. Всего за n дней выполнен объём Sₙ.</p>"


def day_count(a):
    v = a.question.values
    html = line("a_1+a_n=" + n(v["end_sum"]))
    html += "<p>Сумма членов арифметической прогрессии равна полусумме первого и последнего членов, умноженной на их количество. Подставим известную сумму крайних членов:</p>"
    html += line("S_n=" + frac("a_1+a_n", "2") + r"\cdot n")
    html += line("S_n=" + frac(n(v["end_sum"]), "2") + "n=" + n(v["end_sum"] / 2) + "n")
    html += "<p>Весь объём известен. Найдём число дней:</p>"
    html += line(n(v["end_sum"] / 2) + "n=" + n(v["total"]))
    return html + line(
        "n=" + frac(n(2 * v["total"]), n(v["end_sum"])) + "=" + n(a.result)
    )


def last_member(a):
    v = a.question.values
    last = "a_{" + n(a.days) + "}"
    html = line(
        "a_1="
        + n(v["first"])
        + r",\quad n="
        + n(a.days)
        + r",\quad S_n="
        + n(v["total"])
    )
    html += "<p>Воспользуемся формулой суммы арифметической прогрессии, чтобы найти последний член:</p>"
    html += line("S_n=" + frac("a_1+a_n", "2") + r"\cdot n")
    html += line(
        frac(n(v["first"]) + "+" + last, "2")
        + r"\cdot"
        + n(a.days)
        + "="
        + n(v["total"])
    )
    if a.question.kind == "tunnel":
        html += line("a_n=" + frac("2S_n", "n") + "-a_1")
        html += line(
            last + "=" + frac(n(2 * v["total"]), n(a.days)) + "-" + n(v["first"])
        )
    else:
        html += line(
            n(a.days / 2) + "(" + n(v["first"]) + "+" + last + ")=" + n(v["total"])
        )
        html += line(n(v["first"]) + "+" + last + "=" + n(2 * v["total"] / a.days))
    return html + line(last + "=" + n(a.result))


def intermediate(a):
    v = a.question.values
    html = line(
        "a_1="
        + n(v["first"])
        + r",\quad n="
        + n(a.days)
        + r",\quad S_n="
        + n(v["total"])
    )
    html += "<p>Пусть d — ежедневная прибавка. Выразим сумму через первый член, прибавку и число дней:</p>"
    html += line("S_n=" + frac("2a_1+(n-1)d", "2") + r"\cdot n")
    html += line(
        frac("2\\cdot" + n(v["first"]) + "+" + n(a.days - 1) + "d", "2")
        + r"\cdot"
        + n(a.days)
        + "="
        + n(v["total"])
    )
    html += line(
        n(2 * v["first"]) + "+" + n(a.days - 1) + "d=" + n(2 * v["total"] / a.days)
    )
    html += line(n(a.days - 1) + "d=" + n(2 * v["total"] / a.days - 2 * v["first"]))
    html += line("d=" + n(a.difference))
    asked = v["asked"]
    html += f"<p>За {n(asked)}-й день выполнен соответствующий член прогрессии:</p>"
    html += line("a_{" + n(asked) + "}=a_1+(" + n(asked) + "-1)d")
    return html + line(
        "a_{"
        + n(asked)
        + "}="
        + n(v["first"])
        + "+"
        + n(asked - 1)
        + r"\cdot"
        + n(a.difference)
        + "="
        + n(a.result)
    )


def proof(a):
    q = a.question
    if "end_sum" in q.values:
        method = day_count
    elif q.kind in {"tunnel", "tasks"}:
        method = last_member
    else:
        method = intermediate
    return introduction(q) + method(a)
