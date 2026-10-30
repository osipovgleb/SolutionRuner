"""Parent-style substitution and attained angular bounds on physical branches."""

import re

import sympy as sp

from ..probability.common import line
from .angle_questions import X, given_symbols


def trig(q):
    return chr(92) + q.function + " " + q.angle


def substituted(q):
    values = given_symbols(q)
    return re.sub(
        r"\\[a-zA-Z]+|[A-Za-z](?:_\d)?",
        lambda m: r"\left(" + values[m[0]] + r"\right)" if m[0] in values else m[0],
        q.formula,
    )


def angular_interval(a):
    q = a.question
    if q.relation == "eq":
        return sp.FiniteSet(a.angle)
    if q.kind == "lorentz":
        return sp.Interval(a.angle, 180 - a.angle)
    return (
        sp.Interval(q.domain.start, a.angle, left_open=q.domain.left_open)
        if q.maximum
        else sp.Interval(a.angle, q.domain.end, right_open=q.domain.right_open)
    )


def proof(a):
    q = a.question
    relation = {"eq": "=", "ge": r"\geq", "le": r"\leq"}[q.relation]
    increasing = q.function == "sin"
    value_relation = (
        "=" if q.relation == "eq" else r"\geq" if q.maximum != increasing else r"\leq"
    )
    html = "<p>Подставим известные величины в формулу и учтём допустимые углы:</p>"
    html += line(q.angle + r"\in" + sp.latex(q.domain) + r"\quad(\text{градусы})")
    html += line(q.formula if q.kind == "diffraction" else q.quantity + "=" + q.formula)
    if q.kind == "diffraction":
        html += "<p>Период решётки положителен. На допустимом промежутке синус положителен, поэтому выражаем период и используем его верхний предел:</p>"
        html += line(
            r"d=\frac{k\lambda}{\sin " + q.angle + r"}\leq" + sp.latex(q.target)
        )
    else:
        html += line(substituted(q) + relation + q.values["source_values"]["target"])
    html += line(
        sp.latex(q.expression, symbol_names={X: "(" + trig(q) + ")"})
        + relation
        + sp.latex(q.target)
    )
    if q.power == 2:
        html += line(r"\sin^2" + q.angle + value_relation + sp.latex(a.boundary**2))
        html += "<p>На данном промежутке синус положителен. Берём неотрицательный квадратный корень:</p>"
        html += line(
            trig(q)
            + value_relation
            + r"\sqrt{"
            + sp.latex(a.boundary**2)
            + "}="
            + sp.latex(a.boundary)
        )
    else:
        html += line(trig(q) + value_relation + sp.latex(a.boundary))
    monotonic = "возрастает" if increasing else "убывает"
    if q.kind == "lorentz":
        html += "<p>Сначала рассматриваем возрастающую ветвь синуса от 0° до 90°: на ней достигается наименьший допустимый угол.</p>"
    html += (
        "<p>На рассматриваемой ветви тригонометрическая функция "
        + monotonic
        + ". Точному граничному значению соответствует угол:</p>"
    )
    html += line(
        trig(q)
        + "="
        + sp.latex(a.boundary)
        + r"\quad\Longrightarrow\quad "
        + q.angle
        + "="
        + sp.latex(a.angle)
        + "°"
    )
    if q.relation == "eq":
        if q.kind == "flight" and a.angle == 90:
            html += "<p>Получился вертикальный бросок. Условие не исключает прямой угол с горизонтальной поверхностью.</p>"
        return html
    if q.kind == "lorentz":
        html += "<p>Для синуса учитываем и вторую ветвь, затем пересекаем общий ответ с заданным промежутком:</p>"
        html += line(
            q.angle
            + r"\in["
            + sp.latex(a.angle)
            + "+360n;"
            + sp.latex(180 - a.angle)
            + r"+360n],\quad n\in\mathbb Z"
        )
    html += line(
        q.angle + r"\in" + sp.latex(angular_interval(a)) + r"\quad(\text{градусы})"
    )
    if q.multiplier != 1:
        html += "<p>Требуется полный угол между направлениями движения, поэтому удваиваем найденный угол:</p>"
        return html + line(
            "2"
            + q.angle
            + r"=2\cdot"
            + sp.latex(a.angle)
            + "°="
            + sp.latex(a.result)
            + "°"
        )
    label = (
        q.angle
        if q.relation == "eq"
        else "{" + q.angle + "}" + (r"_{\max}" if q.maximum else r"_{\min}")
    )
    return html + line(label + "=" + sp.latex(a.result) + "°")
