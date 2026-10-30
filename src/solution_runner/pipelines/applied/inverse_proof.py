"""Parent-style inverse-power boundaries, with strictly positive denominators."""

from ..probability.common import line
from .formula_proof import final, given, latex


def substitution(q):
    if q.kind == "fuse":
        return r"I=\frac{U}{R}", "I", r"\frac{" + given(q, "voltage") + "}{R}"
    if q.kind == "excavator":
        return (
            r"p=\frac{mg}{2ls}",
            "p",
            r"\frac{"
            + given(q, "mass")
            + r"\cdot"
            + given(q, "gravity")
            + r"}{2\cdot"
            + given(q, "length")
            + r"\cdot s}",
        )
    if q.kind == "column":
        return (
            r"P=\frac{4mg}{\pi D^2}",
            "P",
            r"\frac{4\cdot"
            + given(q, "mass")
            + r"\cdot"
            + given(q, "gravity")
            + "}{"
            + given(q, "pi")
            + r"\cdot D^2}",
        )
    return (
        r"F=\frac{2mS}{t^2}",
        "F",
        r"\frac{2\cdot"
        + given(q, "mass")
        + r"\cdot"
        + given(q, "distance")
        + r"}{t^2}",
    )


def proof(a):
    q = a.question
    general, quantity, substituted = substitution(q)
    relation = {"eq": "=", "le": r"\leq", "ge": r"\geq"}[q.relation]
    reversed_relation = {"eq": "=", "le": r"\geq", "ge": r"\leq"}[q.relation]
    html = "<p>Подставим данные в формулу. Искомая величина положительна, поэтому знаменатель положителен:</p>"
    html += line(general)
    html += line(q.label + ">0")
    if q.kind == "column":
        html += "<p>Найдём диаметр, при котором давление равно предельному:</p>"
        relation = "="
        reversed_relation = "="
    else:
        html += "<p>Запишем требуемое условие и умножим обе части на положительный знаменатель:</p>"
    html += line(quantity + relation + given(q, "target"))
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
