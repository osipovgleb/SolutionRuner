"""All parent pair-rate methods and the unchanged illustrative pair-sum figure."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_chase_proof import section
from .work_extra_models import pair_rates
from .work_sum_proof import conversions, horizon


def paired_times(a):
    return tuple(a.question.values[k] for k in ("t12", "t23", "t13"))


def doubled(a):
    total, rates = pair_rates(a.question)
    html = "<p>Примем весь объём работы за 1. За единицу времени каждая пара выполняет долю, обратную своему времени работы. Сложим производительности пар:</p>"
    html += line(
        "v_{12}+v_{23}+v_{13}="
        + "+".join(frac("1", n(t)) for t in paired_times(a))
        + "="
        + n(sum(rates))
    )
    html += "<p>Каждый участник учтён дважды. При удвоенном числе участников вся работа заняла бы:</p>"
    html += line(
        "t_{\\mathrm{двойное}}=" + frac("1", n(2 * total)) + "=" + n(a.result / 2)
    )
    return (
        html
        + "<p>В действительности участников вдвое меньше, значит, время работы вдвое больше:</p>"
        + line("t=2\\cdot(" + n(a.result / 2) + ")=" + n(a.result))
    )


def common_jobs(a):
    values = paired_times(a)
    common = horizon(values)
    jobs = tuple(common / t for t in values)
    html = "<p>Возьмём общий промежуток времени, равный наименьшему общему кратному времён работы пар:</p>"
    html += line("H=" + n(common))
    html += "<p>За это время пары выполнят следующее число работ. При сложении каждый участник снова учитывается дважды:</p>"
    html += line(
        "N="
        + "+".join(frac(n(common), n(t)) for t in values)
        + "="
        + "+".join(map(n, jobs))
        + "="
        + n(sum(jobs))
    )
    if a.question.kind == "work_pairs_boys":
        html += line(
            "t_{\\mathrm{двойное}}="
            + frac(n(common), n(sum(jobs)))
            + "="
            + n(a.result / 2)
        )
        return html + line("t=2\\cdot(" + n(a.result / 2) + ")=" + n(a.result))
    html += "<p>При обычном числе участников выполненный объём вдвое меньше. Разделим время на этот объём:</p>"
    html += line(
        "N_{\\mathrm{трое}}=" + frac(n(sum(jobs)), "2") + "=" + n(sum(jobs) / 2)
    )
    return html + line("t=" + frac(n(common), n(sum(jobs) / 2)) + "=" + n(a.result))


def system(a):
    total, rates = pair_rates(a.question)
    html = "<p>Обозначим v₁, v₂ и v₃ — производительности трёх участников. Полный объём работы примем за 1. Условия о работе каждой пары дают систему:</p>"
    html += line(
        r"\begin{cases}v_1+v_2="
        + n(rates[0])
        + r",\\v_2+v_3="
        + n(rates[1])
        + r",\\v_1+v_3="
        + n(rates[2])
        + r".\end{cases}"
    )
    html += "<p>Просуммируем левые и правые части уравнений:</p>"
    html += line("2(v_1+v_2+v_3)=" + "+".join(map(n, rates)) + "=" + n(2 * total))
    html += line("v_1+v_2+v_3=" + n(total))
    return html + line("t=" + frac("1", n(total)) + "=" + n(a.result))


def illustration(markup):
    html = "<p><b>Примечание Дмитрия Гущина.</b> Наиболее короткое решение детской задачи, приведённой на рисунке, состоит из одного шага. Какого?</p>"
    html += markup
    html += "<p>Чтобы найти массу четвёртой комбинации, надо сложить первые три и взять от этого половину. Каждая фигура учтена дважды. Это отдельный иллюстративный пример того же приёма:</p>"
    html += line("M=" + frac("10+20+24", "2") + r"=27\,\mathrm{кг}")
    return (
        html
        + "<p>Тот же подход помогает сложить производительности трёх пар в нашей задаче.</p>"
    )


def boys(a, markup):
    return (
        conversions(a.question)
        + section(doubled(a) + illustration(markup), "Решение")
        + section(common_jobs(a), "Приведем другое решение.")
        + section(system(a), "Приведём ещё одно решение.")
    )


def pumps(a):
    return (
        conversions(a.question)
        + section(common_jobs(a), "Решение")
        + section(doubled(a), "Приведем другое решение.")
        + section(system(a), "Алгебраическое решение Тимура Алиева")
    )
