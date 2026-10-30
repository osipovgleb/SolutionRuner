"""Parent-style substitution and attained angular bounds on physical branches."""

import re

import sympy as sp

from ..probability.common import line
from .angle_questions import X, given_symbols


def argument(q):
    return (str(q.argument_multiplier) if q.argument_multiplier != 1 else "") + q.angle


def trig(q):
    return chr(92) + q.function + " " + argument(q)


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
    if q.function == "sin" and q.domain.end * q.argument_multiplier == 180:
        return sp.Interval(a.angle, sp.Rational(180, q.argument_multiplier) - a.angle)
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
    if q.kind == "height":
        value_relation = r"\leq"
    html = "<p>Подставим известные величины в формулу и учтём допустимые углы:</p>"
    domain = q.angle + r"\in" + sp.latex(q.domain)
    if q.argument_multiplier != 1:
        domain += r",\quad " + argument(q) + r"\in" + sp.latex(sp.Interval.open(0, 180))
    html += line(domain + r"\quad(\text{градусы})")
    if q.kind == "height":
        html += "<p>Чтобы мячик прошёл над стеной с указанным запасом, прибавим его к высоте стены:</p>"
        source = q.values["source_values"]
        html += line(
            "H"
            + r"\geq "
            + source["wall"]
            + "+"
            + source["clearance"]
            + "="
            + sp.latex(q.target)
        )
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
    return html + inverse_proof(a)


def inverse_proof(a):
    q = a.question
    increasing = q.function == "sin"
    returning_sine = increasing and q.domain.end * q.argument_multiplier == 180
    html = ""
    monotonic = "возрастает" if increasing else "убывает"
    if returning_sine:
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
        + argument(q)
        + "="
        + sp.latex(a.angle * q.argument_multiplier)
        + "°"
    )
    if q.relation == "eq":
        if q.kind == "flight" and a.angle == 90:
            html += "<p>Получился вертикальный бросок. Условие не исключает прямой угол с горизонтальной поверхностью.</p>"
        return html
    if returning_sine:
        html += "<p>Для синуса учитываем и вторую ветвь, затем пересекаем общий ответ с заданным промежутком:</p>"
        html += line(
            argument(q)
            + r"\in["
            + sp.latex(a.angle * q.argument_multiplier)
            + "+360n;"
            + sp.latex(180 - a.angle * q.argument_multiplier)
            + r"+360n],\quad n\in\mathbb Z"
        )
    if q.argument_multiplier != 1:
        scaled = sp.imageset(
            sp.Lambda(X, q.argument_multiplier * X), angular_interval(a)
        )
        html += line(argument(q) + r"\in" + sp.latex(scaled) + r"\quad(\text{градусы})")
        html += "<p>Делим границы промежутка на 2 и выбираем наименьший допустимый угол:</p>"
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
