"""Sign strips, monotonicity arrows and selected integer points on the source graph."""

from xml.etree import ElementTree as ET

import numpy as np

from ..equations.linear_system_intervals import interval_latex
from ..probability.common import line
from . import tangent_native
from .common import answer
from .graph_reading import NOTE
from .monotonic_sum_input import ordinate

NS = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", NS[1:-1])


RULE = (
    "<p><b>Правило.</b> Если производная положительна, функция возрастает. "
    "Если производная отрицательна, функция убывает.</p>"
)
COUNT_RULE = (
    "<p><b>Правило.</b> Если функция возрастает, её производная положительна. "
    "Если функция убывает, её производная отрицательна. "
    "Точки экстремума не учитываем: в них производная равна нулю.</p>"
)
EXTREMA_RULE = (
    "<p><b>Правило.</b> В точке максимума функция переходит от возрастания к убыванию, "
    "а в точке минимума — от убывания к возрастанию.</p>"
)


def endpoint_solution(figure, graph):
    question = graph.question
    point = graph.integers[0]
    span_name = (
        "отрезок"
        if question.span.lower_closed and question.span.upper_closed
        else "промежуток"
    )
    if point in (question.span.lower, question.span.upper):
        side = "левом" if point == question.span.lower else "правом"
        rising = (side == "правом") == (question.target == "наибольшее")
        explanation = (
            "На заданном промежутке функция "
            + ("возрастает" if rising else "убывает")
            + f", поэтому {question.target} значение достигается на {side} конце."
        )
    else:
        change = (
            "от возрастания к убыванию"
            if question.target == "наибольшее"
            else "от убывания к возрастанию"
        )
        explanation = f"На заданном промежутке функция переходит {change}. В точке перехода она принимает {question.target} значение."
    return (
        RULE
        + figure
        + f'<p>Рассматриваем {span_name} <span data-inline-latex="'
        + interval_latex(question.span)
        + '"></span>. '
        + explanation
        + "</p>"
        + line(f"x_0={point}")
        + NOTE
    )


def derivative_extrema_solution(figure, graph):
    rules = {
        "max": "В точке максимума производная меняет знак с плюса на минус.",
        "min": "В точке минимума производная меняет знак с минуса на плюс.",
        "extrema": "В точке экстремума производная меняет знак. Переход с плюса на минус даёт максимум, с минуса на плюс — минимум.",
    }
    kind = {"max": "максимума", "min": "минимума", "extrema": "экстремума"}
    question = graph.question
    selection = (
        '<p>На заданном промежутке <span data-inline-latex="'
        + interval_latex(question.interval)
        + '"></span> '
    )
    if question.operation == "point":
        return (
            "<p><b>Правило.</b> "
            + rules[question.target]
            + "</p>"
            + figure
            + selection
            + f"отмечена единственная точка {kind[question.target]} функции.</p>"
            + line(f"x={graph.result}")
            + NOTE
        )
    return (
        "<p><b>Правило.</b> "
        + rules[question.target]
        + "</p>"
        + figure
        + selection
        + "отмечены точки "
        + kind[question.target]
        + " функции. Их количество — "
        + graph.result
        + ".</p>"
        + NOTE
    )


def longest_interval_solution(figure, graph):
    interval = graph.longest
    change = "возрастания" if graph.question.sign > 0 else "убывания"
    lower = answer(interval.lower)
    left_term = f"({lower})" if interval.lower < 0 else lower
    return (
        RULE
        + figure
        + f'<p>Самый длинный промежуток {change} — <span data-inline-latex="'
        + interval_latex(interval)
        + '"></span>. Его длина:</p>'
        + line(f"L={answer(interval.upper)}-{left_term}={graph.result}")
        + NOTE
    )


def solution(figure, values, *, count=False, extrema=False):
    if extrema:
        points = r",\ ".join(map(str, values))
        terms = "+".join("(" + str(n) + ")" if n < 0 else str(n) for n in values)
        return (
            EXTREMA_RULE
            + figure
            + '<p>На графике отмечены точки экстремума с абсциссами <span data-inline-latex="'
            + points
            + '"></span>. Их сумма:</p>'
            + line("S=" + terms + "=" + str(sum(values)))
            + NOTE
        )
    return (COUNT_RULE if count else RULE) + figure + proof(values, count=count) + NOTE


def proof(values, *, count=False):
    points = r",\ ".join(map(str, values))
    if count:
        return (
            '<p>На промежутках возрастания отмечены целые точки <span data-inline-latex="'
            + points
            + '"></span>. Их количество — '
            + str(len(values))
            + ".</p>"
        )
    total = "+".join("(" + str(n) + ")" if n < 0 else str(n) for n in values)
    return (
        '<p>В эти промежутки входят целые точки <span data-inline-latex="'
        + points
        + '"></span>. Их сумма:</p>'
        + line("S=" + total + "=" + str(sum(values)))
    )


def stationary_solution(figure, graph):
    scope = (
        'На отрезке <span data-inline-latex="'
        + interval_latex(graph.question.span)
        + '"></span> отмечены точки с горизонтальной касательной. '
        if graph.question.span
        else "На графике отмечены точки с горизонтальной касательной. "
    )
    return (
        "<p><b>Правило.</b> Производная функции равна нулю в точках, "
        "в которых касательная к её графику горизонтальна.</p>"
        + figure
        + "<p>"
        + scope
        + f"Их количество — {graph.result}.</p>"
        + NOTE
    )


def neighborhood_solution(figure, graph):
    verb = "возрастает" if graph.question.sign > 0 else "убывает"
    points = r",\ ".join(map(str, graph.integers))
    return (
        "<p><b>Правило.</b> Учитываем точки, в окрестности которых функция "
        + verb
        + ". В точках экстремума направление изменения функции меняется.</p>"
        + figure
        + "<p>Красным показано возрастание, зелёным — убывание.</p>"
        + '<p>Подходящие целые точки имеют абсциссы <span data-inline-latex="'
        + points
        + f'"></span>. Их количество — {graph.result}.</p>'
        + NOTE
    )


def render(graph, *, stroke_scale=1.0):
    root = ET.fromstring(graph.source)
    if any(node.get("style") or node.tag == NS + "style" for node in root.iter()):
        root = ET.fromstring(tangent_native.presentation(graph.source))
    vx, vy, width, height = map(float, root.get("viewBox").split())
    entry = graph.entry
    unit = entry["svg_unit"]
    ox, oy = entry["svg_origin"]
    xu = entry.get("x_unit", unit)
    extrema = graph.question.operation == "sum" and not graph.question.derivative
    show_signs = not extrema and graph.question.operation != "stationary"
    strip = 1.85 * unit if show_signs else 0
    top = vy - strip
    root.set("viewBox", f"{vx} {top} {width} {height + strip}")
    root.set("height", str(height + strip))
    root.set("width", str(width))
    layer = ET.SubElement(root, NS + "g", {"id": "derivative-signs-and-integers"})

    def element(tag, **attrs):
        if stroke_scale != 1.0:
            for name in ("stroke_width", "r"):
                if name in attrs:
                    attrs[name] = float(attrs[name]) * stroke_scale
            if "stroke_dasharray" in attrs:
                attrs["stroke_dasharray"] = " ".join(
                    str(float(value) * stroke_scale)
                    for value in attrs["stroke_dasharray"].split()
                )
        return ET.SubElement(
            layer, NS + tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()}
        )

    # No new grid cells: only a white sign/arrow strip above the original drawing.
    if show_signs:
        element("rect", x=vx, y=top, width=width, height=strip, fill="white")
    bands = () if extrema else graph.bands
    zeros = () if extrema else graph.zeros
    if not graph.question.derivative:
        # Native export handles can be horizontal inside a monotone interval.
        # Preserve them in the strict derivative count, but annotate changes of
        # direction rather than split one arrow into redundant same-sign pieces.
        merged = []
        for a, b, sign in bands:
            if merged and merged[-1][2] == sign:
                merged[-1] = (merged[-1][0], b, sign)
            else:
                merged.append((a, b, sign))
        bands = tuple(merged)
        boundaries = [b for _, b, _ in bands[:-1]]
        zeros = tuple(
            (x, y) for x, y in zeros if any(abs(x - b) < 1e-6 for b in boundaries)
        )
    for x, y in zeros:
        element(
            "line",
            x1=x,
            x2=x,
            y1=top,
            y2=vy + height,
            stroke="#007EA5",
            stroke_width=".85",
            stroke_dasharray="3 2",
            opacity=".85",
        )
        if y is not None:
            element(
                "circle",
                cx=x,
                cy=oy if graph.question.derivative else y,
                r=1.9,
                fill="#007EA5",
            )
    point = graph.question.operation == "point" and graph.question.derivative
    selection = graph.longest or (
        graph.question.span
        if graph.question.operation in ("global", "stationary")
        else graph.question.interval
        if graph.question.operation in ("count", "point") and graph.question.derivative
        else None
    )
    if graph.longest is not None:
        element(
            "line",
            x1=ox + float(selection.lower) * xu,
            x2=ox + float(selection.upper) * xu,
            y1=oy,
            y2=oy,
            stroke="#2563eb",
            stroke_width=2.2,
        )
    elif selection is not None:
        domain = graph.question.domain
        for bound in (selection.lower, selection.upper):
            if domain is not None and not domain.lower < bound < domain.upper:
                continue
            px = ox + float(bound) * xu
            element(
                "line",
                x1=px,
                x2=px,
                y1=vy if point else top,
                y2=vy + height,
                stroke="#2563eb",
                stroke_width=2.2,
            )
    for a, b, sign in bands:
        mid = (a + b) / 2
        color = "#15803d" if sign > 0 else "#b42318"
        node = element(
            "text",
            x=mid,
            y=top + 0.62 * unit,
            text_anchor="middle",
            font_family="Times New Roman",
            font_size=0.72 * unit,
            fill=color,
        )
        node.text = "+" if sign > 0 else "−"
        half = min(0.7 * unit, (b - a) * 0.31)
        x1, x2 = mid - half, mid + half
        y1, y2 = (
            (top + 1.53 * unit, top + 0.94 * unit)
            if sign > 0
            else (top + 0.94 * unit, top + 1.53 * unit)
        )
        element(
            "path",
            d=f"M{x1},{y1} L{x2},{y2}",
            stroke=color,
            stroke_width=1.25,
            fill="none",
            stroke_linecap="round",
        )
        direction = np.array([x2 - x1, y2 - y1])
        length = np.linalg.norm(direction)
        ux, uy = direction / length
        size = min(0.23 * unit, length * 0.3)
        element(
            "path",
            d=f"M{x2 - size * ux - size * 0.5 * uy},{y2 - size * uy + size * 0.5 * ux} L{x2},{y2} L{x2 - size * ux + size * 0.5 * uy},{y2 - size * uy - size * 0.5 * ux}",
            stroke=color,
            stroke_width=1.25,
            fill="none",
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    for px, py in graph.marks:
        if graph.question.operation == "stationary":
            element(
                "line",
                x1=px,
                x2=px,
                y1=oy,
                y2=py,
                stroke="#007EA5",
                stroke_width=".85",
                stroke_dasharray="3 2",
            )
        element(
            "circle",
            cx=px,
            cy=py,
            r=0.16 * unit,
            fill="#15803d",
            stroke="white",
            stroke_width=0.7,
        )
    undefined = [
        p["x"] for p in entry.get("zero_points", []) if not p.get("defined", True)
    ]
    for n in graph.integers:
        px = ox + n * xu
        on_axis = (
            graph.question.derivative
            and graph.question.operation == "sum"
            and (
                n in undefined
                or n in (graph.question.domain.lower, graph.question.domain.upper)
            )
        )
        py = oy if on_axis else ordinate(entry, px)
        if extrema or point:
            px, py = min(graph.zeros, key=lambda xy: abs(xy[0] - px))
        if (
            graph.question.operation == "global"
            and graph.question.span.lower < n < graph.question.span.upper
        ):
            px, py = min(graph.zeros, key=lambda xy: abs(xy[0] - px))
        element(
            "circle",
            cx=px,
            cy=py,
            r=0.13 * unit,
            fill="#15803d",
            stroke="white",
            stroke_width=0.7,
            data_integer_abscissa=n,
        )
        text = str(n).replace("-", "−")
        tx, ty = px + 0.22 * unit, py - 0.3 * unit
        label_width = max(0.4 * unit, len(text) * 0.31 * unit)
        element(
            "rect",
            x=tx - label_width / 2,
            y=ty - 0.53 * unit,
            width=label_width,
            height=0.65 * unit,
            fill="white",
            rx=1.5,
        )
        label = element(
            "text",
            x=tx,
            y=ty,
            fill="#15803d",
            font_size=0.55 * unit,
            font_family="Times New Roman",
            text_anchor="middle",
        )
        label.text = text
    return ET.tostring(root, encoding="unicode")
