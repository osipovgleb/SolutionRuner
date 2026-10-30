"""Keep the parent method: level inequality, time interval, duration and share."""

import sympy as sp

from ..probability.common import line

T = sp.Symbol("t", real=True)


def phase(q):
    degrees = q.frequency * T + q.phase
    return sp.latex(degrees if q.kind == "sensor" else degrees * sp.pi / 180)


def period_bounds(a):
    q = a.question
    lower, upper = a.base
    scale = 1 if q.kind == "sensor" else sp.pi / 180
    period = 360 * scale
    left, right = ("(", ")") if q.strict else ("[", "]")
    html = line(
        phase(q)
        + r"\in"
        + left
        + sp.latex(lower * scale)
        + "+"
        + sp.latex(period)
        + " n;"
        + sp.latex(upper * scale)
        + "+"
        + sp.latex(period)
        + " n"
        + right
        + r",\quad n\in\mathbb Z"
    )
    html += line(
        "t"
        + r"\in"
        + left
        + sp.latex((lower - q.phase) / q.frequency)
        + "+"
        + sp.latex(360 / q.frequency)
        + " n;"
        + sp.latex((upper - q.phase) / q.frequency)
        + "+"
        + sp.latex(360 / q.frequency)
        + " n"
        + right
        + r",\quad n\in\mathbb Z"
    )
    return html


def duration_line(a):
    pieces = a.times.args if isinstance(a.times, sp.Union) else [a.times]
    differences = [
        r"\left(" + sp.latex(piece.end) + "-" + sp.latex(piece.start) + r"\right)"
        for piece in pieces
        if isinstance(piece, sp.Interval)
    ]
    return line(
        r"\Delta t="
        + ("+".join(differences) + "=" if differences else "")
        + sp.latex(a.duration)
        + r"\,\mathrm{с}"
    )


def proof(a, result):
    q = a.question
    relation = ">" if q.strict else r"\geq"
    trig = chr(92) + q.function + r"\left(" + phase(q) + r"\right)"
    quantity = "U" if q.kind == "sensor" else "v(t)"
    html = "<p>Задача сводится к решению неравенства для заданного закона изменения величины:</p>"
    html += line(quantity + "=" + q.formula)
    html += line(sp.latex(q.amplitude) + r"\cdot" + trig + relation + sp.latex(q.level))
    html += line(trig + relation + sp.latex(a.ratio))
    if q.kind == "sensor":
        html += "<p>Аргумент функции и частота в следующих формулах выражены в градусах. Учитываем все периоды и ограничиваем время первой секундой:</p>"
    else:
        html += "<p>Аргумент выражен в радианах. Учитываем периоды и пересекаем найденные промежутки с заданным временем наблюдения:</p>"
    if a.base is not None:
        html += period_bounds(a)
    else:
        html += "<p>Сравним порог со всей областью значений тригонометрической функции от −1 до 1.</p>"
    html += line(r"t\in[0;" + sp.latex(q.window) + r"],\qquad t\in" + sp.latex(a.times))
    html += "<p>Найдём суммарную длительность и разделим её на всё время наблюдения. Отдельные граничные моменты на длительность не влияют:</p>"
    html += duration_line(a)
    html += line(r"\frac{\Delta t}{" + sp.latex(q.window) + "}=" + sp.latex(a.fraction))
    if q.kind == "sensor":
        return html + line(
            sp.latex(a.fraction) + r"\cdot100\%=" + sp.latex(a.result) + r"\%"
        )
    rendered = result.replace(",", "{,}")
    return html + line(
        sp.latex(a.fraction)
        + ("=" if sp.Rational(result.replace(",", ".")) == a.result else r"\approx")
        + rendered
    )
