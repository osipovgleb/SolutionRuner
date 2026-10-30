"""Parent-style inverse-power boundaries, with strictly positive denominators."""

from string import Template

from ..probability.common import line
from .formula_proof import final, given, latex

_FORMULAS = {
    "boiler": (
        r"\eta=\frac{c_{\mathrm{в}}m_{\mathrm{в}}(t_2-t_1)}{q_{\mathrm{др}}m_{\mathrm{др}}}\cdot100\%",
        r"\eta",
        r"\frac{($heat)\cdot$water\cdot($end-$start)}{($fuel)\cdot m_{\mathrm{др}}}\cdot100",
    ),
    "fuse": (r"I=\frac{U}{R}", "I", r"\frac{$voltage}{R}"),
    "excavator": (
        r"p=\frac{mg}{2ls}",
        "p",
        r"\frac{$mass\cdot$gravity}{2\cdot$length\cdot s}",
    ),
    "column": (
        r"P=\frac{4mg}{\pi D^2}",
        "P",
        r"\frac{4\cdot$mass\cdot$gravity}{$pi\cdot D^2}",
    ),
    "traction": (r"F=\frac{2mS}{t^2}", "F", r"\frac{2\cdot$mass\cdot$distance}{t^2}"),
}


def substitution(q):
    general, quantity, template = _FORMULAS[q.kind]
    values = {key: value.replace(" ", "") for key, value in q.source_values.items()}
    return general, quantity, Template(template).substitute(values)


def proof(a):
    q = a.question
    general, quantity, substituted = substitution(q)
    relation = {"eq": "=", "le": r"\leq", "ge": r"\geq"}[q.relation]
    reversed_relation = {"eq": "=", "le": r"\geq", "ge": r"\leq"}[q.relation]
    html = "<p>Подставим данные в формулу. Искомая величина положительна, поэтому знаменатель положителен:</p>"
    html += line(general)
    html += line(q.label + ">0")
    if q.kind == "boiler":
        html += line(
            r"\Delta t="
            + given(q, "end")
            + "-"
            + given(q, "start")
            + "="
            + latex(q, q.values["end"] - q.values["start"])
            + r"\ {}^{\circ}\mathrm{C}"
        )
    if q.kind == "column":
        html += "<p>Найдём диаметр, при котором давление равно предельному:</p>"
        relation = "="
        reversed_relation = "="
    else:
        html += "<p>Запишем требуемое условие и умножим обе части на положительный знаменатель:</p>"
    html += line(
        quantity + relation + given(q, "target") + (r"\%" if q.kind == "boiler" else "")
    )
    html += line(substituted + relation + given(q, "target"))
    if q.kind == "fuse":
        html += line(given(q, "voltage") + relation + latex(q, q.target) + q.label)
    else:
        html += line(latex(q, a.expression) + relation + latex(q, q.target))
    power = q.label + ("^2" if a.power == 2 else "")
    html += line(power + reversed_relation + latex(q, a.ratio))
    if a.power == 2:
        html += line(
            q.label
            + reversed_relation
            + r"\sqrt{"
            + latex(q, a.ratio)
            + "}="
            + latex(q, a.result)
        )
    if q.kind == "column":
        html += "<p>При меньшем диаметре давление больше предельного. При увеличении положительного диаметра давление уменьшается, поэтому найденный диаметр — наименьший допустимый.</p>"
    elif q.relation != "eq":
        html += "<p>На положительной полуоси обратная степенная зависимость убывает. Граничное значение допускается условием и даёт искомый экстремум.</p>"
    return html + final(a, maximum=q.relation == "ge", minimum=q.relation == "le")
