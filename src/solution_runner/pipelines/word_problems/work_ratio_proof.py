"""The four proportional-worker methods and the apprentice's two work shares."""

from html import escape

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section
from .work_sum_proof import conversions


def inline(formula):
    return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'


def reciprocal(a):
    v = a.question.values
    ratio = v["span1"] / v["span2"]
    r2 = frac(n(ratio.p), n(ratio.q) + "x")
    t2 = frac(n(ratio.q) + "x", n(ratio.p))
    html = "<p>Пусть первый рабочий один выполнит работу за x дней. Второй за указанное число дней выполняет столько же, сколько первый за своё число дней. Поэтому отношение их производительностей равно:</p>"
    html += line(
        frac("v_2", "v_1") + "=" + frac(n(v["span1"]), n(v["span2"])) + "=" + n(ratio)
    )
    html += line("x>" + n(v["joint"]))
    html += "<p>Объём работы не задан, примем его за 1. Производительность равна отношению работы ко времени её выполнения:</p>"
    html += line(r"v=\frac{A}{t}")
    html += (
        "<table><tbody><tr><th></th><th>Производительность (ед. раб./день)</th><th>Время работы (дней)</th><th>Работа (ед.)</th></tr><tr><td>Первый рабочий</td><td>"
        + inline(frac("1", "x"))
        + "</td><td>"
        + inline("x")
        + "</td><td>1</td></tr><tr><td>Второй рабочий</td><td>"
        + inline(r2)
        + "</td><td>"
        + inline(t2)
        + "</td><td>1</td></tr></tbody></table>"
    )
    html += "<p>Работая вместе, рабочие выполняют всю работу за указанное число дней. Производительности складываются:</p>"
    html += line(frac("1", "x") + "+" + r2 + "=" + frac("1", n(v["joint"])))
    html += line(frac(n(1 + ratio), "x") + "=" + frac("1", n(v["joint"])))
    return html + line(
        "x=" + n(v["joint"]) + r"\cdot(" + n(1 + ratio) + ")=" + n(a.result)
    )


def system(a):
    v = a.question.values
    ratio = v["span1"] / v["span2"]
    first_rate, second_rate = 1 / a.result, ratio / a.result
    html = "<p>Сведём задачу к системе уравнений. Обозначим v₁ и v₂ — доли работы, выполняемые первым и вторым рабочим за день. Полный объём примем за 1:</p>"
    html += line(
        r"\begin{cases}"
        + n(v["joint"])
        + r"(v_1+v_2)=1,\\"
        + n(v["span1"])
        + "v_1="
        + n(v["span2"])
        + r"v_2.\end{cases}"
    )
    html += line("v_2=" + n(ratio) + "v_1")
    html += line(n(v["joint"]) + "(1+" + n(ratio) + ")v_1=1")
    html += line("v_1=" + n(first_rate) + r",\quad v_2=" + n(second_rate))
    return (
        html
        + "<p>Время самостоятельной работы первого рабочего обратно его производительности:</p>"
        + line("t_1=" + frac("1", n(first_rate)) + "=" + n(a.result))
    )


def norms(a):
    v = a.question.values
    ratio = v["span1"] / v["span2"]
    html = "<p>Пусть первый рабочий за день выполняет некоторую часть работы; назовём её нормой. Второй выполняет указанную долю нормы, а вместе они выполняют сумму норм:</p>"
    html += line(
        "N_1=1,\\quad N_2=" + n(ratio) + r",\quad N=1+" + n(ratio) + "=" + n(1 + ratio)
    )
    html += "<p>За время совместной работы они выполнят всю работу. Найдём число норм в ней:</p>"
    html += line("A=" + n(v["joint"]) + r"\cdot(" + n(1 + ratio) + ")=" + n(a.result))
    return (
        html
        + "<p>Первый рабочий один выполняет одну норму в день, поэтому столько же дней потребуется на всю работу.</p>"
    )


def comparison(a):
    v = a.question.values
    factor = v["span2"] / v["span1"]
    second_time = v["joint"] * (1 + factor)
    if factor > 1:
        html = "<p>Первый рабочий работает быстрее второго в указанное число раз:</p>"
    elif factor < 1:
        html = "<p>Производительность первого рабочего составляет следующую долю производительности второго:</p>"
    else:
        html = "<p>Производительности рабочих равны:</p>"
    html += line(frac("v_1", "v_2") + "=" + n(factor))
    html += "<p>Вместе они работают быстрее одного второго рабочего. Поэтому второй, работая один, затратил бы больше времени на тот же заказ:</p>"
    html += line("t_2=" + n(v["joint"]) + "(1+" + n(factor) + ")=" + n(second_time))
    html += "<p>Время первого рабочего обратно отношению производительностей:</p>"
    return html + line("t_1=" + frac(n(second_time), n(factor)) + "=" + n(a.result))


def ratio_workers(a):
    return (
        section(reciprocal(a), "Решение")
        + section(system(a), "Приведем другое решение.")
        + section(norms(a), "Приведем арифметическое решение.")
        + section(
            comparison(a), "Приведем ещё одно арифметическое решение (Павел Юкляев)"
        )
    )


def apprentice(a):
    q, v = a.question, a.question.values
    first_time = v["ratio"] * v["apprentice"] / (v["ratio"] + 1)
    master_time = v["master"] / (v["ratio"] + 1)
    factor = v["ratio"] * v["apprentice"] / v["master"]
    html = conversions(q)
    html += "<p>Производительности ученика и токаря равны:</p>"
    html += line(
        r"v_{\mathrm{уч}}="
        + frac("1", n(v["apprentice"]))
        + r",\quad v_{\mathrm{ток}}="
        + frac("1", n(v["master"]))
    )
    html += "<p>Пусть a — время работы ученика, а b — время работы токаря. Вся работа равна 1, а ученик изготовил указанное число долей относительно токаря:</p>"
    html += line(
        r"\begin{cases}"
        + frac("a", n(v["apprentice"]))
        + "+"
        + frac("b", n(v["master"]))
        + r"=1,\\"
        + frac("a", n(v["apprentice"]))
        + "="
        + n(v["ratio"])
        + r"\cdot"
        + frac("b", n(v["master"]))
        + r".\end{cases}"
    )
    html += line("a=" + n(factor) + "b")
    html += line(
        frac(n(factor) + "b", n(v["apprentice"]))
        + "+"
        + frac("b", n(v["master"]))
        + "=1"
    )
    html += line("b=" + n(master_time) + r",\quad a=" + n(first_time))
    return (
        html
        + "<p>Они заканчивают работу одновременно, поэтому токарю нужно начать позже ученика на разность времён работы:</p>"
        + line("a-b=" + n(first_time) + "-" + n(master_time) + "=" + n(a.result))
    )
