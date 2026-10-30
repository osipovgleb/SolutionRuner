"""Stationary points of a function, motion graph or primitive share one selection."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction

from ..core.numbers import parse_rational
from ..equations.linear_system_intervals import Interval, interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import graph_input
from .common import answer

_NUMBER = r"-?\d+(?:[,.]\d+)?"
_PREFIX = re.compile(
    r"На рисунке изображен график функции (?P<curve>(?:y=)?f\(x\)|y=F\(x\))"
    r"(?P<primitive>\s*(?:,\s*|—\s*)?одной из первообразных(?: некоторой)? функции f\(x\))?"
    r",?\s*определенной на интервале(?P<domain>\([^)]*\))\. (?P<request>.+)"
)
_MOTION = re.compile(
    r"Материальная точка M начинает движение из точки A и движется по прямой на протяжении (?P<end>\d+) секунд\. "
    r"График показывает, как менялось расстояние от точки A до точки M со временем\. "
    r"На оси абсцисс откладывается время t в секундах, на оси ординат — расстояние s\. "
    r"Определите, сколько раз за время движения скорость точки M обращалась в ноль"
    r"\(начало и конец движения не учитывайте\)\."
)
_NS = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class Question:
    kind: str
    domain: Interval
    interval: Interval
    horizontal: Fraction | None = None
    include_coincident: bool = False


def interval(text):
    match = re.fullmatch(rf"([\[(])({_NUMBER});\s*({_NUMBER})([\])])", text)
    if not match:
        raise UnsupportedCondition("a finite explicit graph interval is required")
    lower, upper = parse_rational(match[2]), parse_rational(match[3])
    if lower >= upper:
        raise UnsupportedCondition("graph interval endpoints must be ordered")
    return Interval(lower, upper, match[1] == "[", match[4] == "]")


def parse(text):
    text = text.replace("−", "-").replace("–", "-")
    motion = _MOTION.fullmatch(text)
    if motion:
        domain = Interval(Fraction(0), Fraction(motion["end"]))
        if domain.upper <= 0:
            raise UnsupportedCondition("positive motion duration is required")
        return Question("motion", domain, domain)
    match = _PREFIX.fullmatch(text)
    if not match:
        raise UnsupportedCondition("unsupported complete stationary-point question")
    primitive = match["curve"] == "y=F(x)"
    if primitive != bool(match["primitive"]):
        raise UnsupportedCondition("the graph must explicitly be the stated primitive")
    domain = interval(match["domain"])
    request = match["request"]
    horizontal = re.fullmatch(
        rf"Найдите количество точек, в которых касательная к графику функции параллельна прямой y=({_NUMBER})(?P<coincident> или совпадает с ней)?\.",
        request,
    )
    if horizontal and not primitive:
        return Question(
            "horizontal",
            domain,
            domain,
            parse_rational(horizontal[1]),
            bool(horizontal["coincident"]),
        )
    if request == "Найдите корень уравнения f'(x)=0." and not primitive:
        return Question("root", domain, domain)
    if (
        re.fullmatch(
            r"Найдите количество точек, в которых производная функции f\(x\)\s*равна 0\.",
            request,
        )
        and not primitive
    ):
        return Question("count", domain, domain)
    count = re.fullmatch(
        r"(?:Найдите|Пользуясь рисунком, определите) количество "
        r"(?:решений уравнения (?P<equation>f'\(x\)|f\(x\))=0|точек, в которых производная функции равна нулю) "
        r"на отрезке (?P<interval>\[[^]]*\])\.?",
        request,
    )
    if count and (count["equation"] == "f(x)") == primitive:
        return Question(
            "primitive" if primitive else "count", domain, interval(count["interval"])
        )
    raise UnsupportedCondition("the entire stationary-point request must be recognized")


def select(points, span, *, svg_order=False):
    selected = []
    previous = None
    for point in points:
        if point.get("kind") not in {"max", "min", "stationary"}:
            raise UnsupportedCondition(
                "a reviewed type of stationary point is required"
            )
        if "x" in point:
            lower = upper = Fraction(point["x"])
        else:
            lower, upper = map(Fraction, point["x_bounds"])
            if lower >= upper:
                raise UnsupportedCondition("stationary-point bounds must be ordered")
        position = point["svg"][0] if svg_order else lower
        if previous is not None and position <= previous:
            raise UnsupportedCondition(
                "stationary points must have disjoint ordered bounds"
            )
        previous = point["svg"][0] if svg_order else upper
        lower_open, upper_open = point.get("x_bounds_open", [False, False])
        outside = (
            upper < span.lower
            or lower > span.upper
            or upper == span.lower
            and (not span.lower_closed or upper_open)
            or lower == span.upper
            and (not span.upper_closed or lower_open)
        )
        inside = (
            lower > span.lower
            or lower == span.lower
            and (span.lower_closed or lower_open)
        ) and (
            upper < span.upper
            or upper == span.upper
            and (span.upper_closed or upper_open)
        )
        if inside:
            selected.append(point)
        elif not outside:
            raise UnsupportedCondition(
                "the source does not resolve a stationary point at the requested boundary"
            )
    return selected


def parallel_points(points, ordinate, include_coincident):
    if include_coincident:
        return points
    result = []
    for point in points:
        if "y" in point:
            if Fraction(point["y"]) != ordinate:
                result.append(point)
        else:
            if "y_bounds" not in point:
                raise UnsupportedCondition("the stationary ordinate is not specified")
            lower, upper = map(Fraction, point["y_bounds"])
            if lower <= ordinate <= upper:
                raise UnsupportedCondition(
                    "the graph does not resolve coincidence with the horizontal line"
                )
            result.append(point)
    return result


def _input(context):
    data = graph_input.read_graph(context)
    question = parse(data[4])
    entry = data[5]
    expected_curve = (
        "s"
        if question.kind == "motion"
        else "F"
        if question.kind == "primitive"
        else "f"
    )
    if entry.get("curve_name") != expected_curve or tuple(
        map(Fraction, entry.get("domain", ()))
    ) != (question.domain.lower, question.domain.upper):
        raise UnsupportedCondition(
            "the audited curve and its domain must match the question"
        )
    span = question.interval
    if (
        span.lower < question.domain.lower
        or span.upper > question.domain.upper
        or span.lower == question.domain.lower
        and span.lower_closed
        or span.upper == question.domain.upper
        and span.upper_closed
    ):
        raise UnsupportedCondition(
            "the requested interval must lie in the open graph domain"
        )
    points = entry.get("stationary_points")
    if not isinstance(points, list) or len(select(points, question.domain)) != len(
        points
    ):
        raise UnsupportedCondition(
            "a complete transcription of the interior stationary points is required"
        )
    selected = select(points, span)
    if question.kind == "horizontal":
        selected = parallel_points(
            selected, question.horizontal, question.include_coincident
        )
    if question.kind == "root" and (len(selected) != 1 or "x" not in selected[0]):
        raise UnsupportedCondition("a unique exactly read root is required")
    return data, question, selected


def required_assets(context):
    data, _, _ = _input(context)
    return graph_input.requirements(data[5])


def render_svg(entry, source, span, selected):
    root = ET.fromstring(source)
    for node in root.iter():
        for attr in ("stroke", "fill"):
            if node.get(attr) == "#143B8F":
                node.set(attr, "#000000")
    group = ET.SubElement(
        root, "{" + _NS + "}g", {"data-runner-diagram": "stationary_points"}
    )

    def node(tag, **attrs):
        return ET.SubElement(
            group,
            "{" + _NS + "}" + tag,
            {k.replace("_", "-"): str(v) for k, v in attrs.items()},
        )

    ox, _ = entry["svg_origin"]
    unit = entry["svg_unit"]
    top, bottom = entry["svg_bracket_y"]
    for xvalue, direction in [(span.lower, 1), (span.upper, -1)]:
        x = ox + float(xvalue) * unit
        arm = direction * 9.7
        node(
            "polyline",
            points=f"{x + arm},{top} {x},{top} {x},{bottom} {x + arm},{bottom}",
            fill="none",
            stroke="#143B8F",
            stroke_width=1.25,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    for point in selected:
        x, y = point["svg"]
        node(
            "circle",
            cx=x,
            cy=y,
            r=2.3,
            fill="#007EA5",
            stroke="#007EA5",
            stroke_width=0.75,
        )
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    data, question, selected = _input(context)
    entry, source = data[5:]
    return (
        (
            solution_diagrams.spec(
                entry["diagram_key"],
                render_svg(entry, source, question.interval, selected),
            ),
        )
        if entry.get("highlight_stationary")
        else ()
    )


def proof(question, points):
    count = len(points)
    span = interval_latex(question.interval)
    if question.kind == "motion":
        html = (
            "<p>Мгновенная скорость равна производной расстояния по времени:</p>"
            + line("v(t)=s'(t)")
        )
        html += (
            "<p>Скорость обращается в ноль там, где касательная к графику s(t) горизонтальна. Начало и конец движения не учитываем:</p>"
            + line(r"0<t<" + answer(question.interval.upper))
        )
    elif question.kind == "primitive":
        html = (
            "<p>По определению первообразной на данном интервале справедливо равенство:</p>"
            + line("f(x)=F'(x)")
        )
        html += (
            "<p>Поэтому решениями уравнения f(x)=0 являются точки, в которых касательная к изображённому графику F горизонтальна:</p>"
            + line("f(x)=0" + r"\iff F'(x)=0")
        )
    elif question.kind == "horizontal":
        html = "<p>У данной прямой угловой коэффициент равен нулю:</p>" + line(
            "y=" + answer(question.horizontal) + r"\quad\Longrightarrow\quad k=0"
        )
        html += (
            "<p>Угловой коэффициент касательной равен значению производной в точке касания. Поэтому ищем горизонтальные касательные:</p>"
            + line("f'(x)=k=0")
        )
    else:
        html = (
            "<p>Производная функции равна нулю в точках, в которых касательная к её графику параллельна оси абсцисс:</p>"
            + line("f'(x)=0" + r"\iff k=0")
        )
    if question.kind == "horizontal" and not question.include_coincident:
        html += (
            "<p>Совпадающую с заданной прямой касательную не считаем: в точке касания ордината должна отличаться от ординаты этой прямой.</p>"
            + line("f(x)" + r"\ne " + answer(question.horizontal))
        )
    if question.kind == "root":
        value = answer(points[0]["x"])
        html += (
            "<p>На заданном интервале такая точка одна. По сетке читаем её абсциссу:</p>"
            + line("x=" + value)
        )
        return value, html
    maxima = sum(p["kind"] == "max" for p in points)
    minima = sum(p["kind"] == "min" for p in points)
    other = count - maxima - minima
    html += (
        "<p>На данном рисунке считаем подходящие точки с горизонтальной касательной, лежащие в заданном промежутке:</p>"
        + line("x\\in " + span)
    )
    html += line(r"N_{\max}=" + str(maxima)) + line(r"N_{\min}=" + str(minima))
    if other:
        html += (
            "<p>Учитываем также стационарные точки, не являющиеся экстремумами:</p>"
            + line(r"N_{\mathrm{прочие}}=" + str(other))
        )
    html += line(
        "N="
        + "+".join(map(str, [maxima, minima] + ([other] if other else [])))
        + "="
        + str(count)
    )
    return str(count), html


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question, selected = _input(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(question, selected)
    svg = (
        render_svg(entry, source, question.interval, selected)
        if entry.get("highlight_stationary")
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated_solution_assets
    )
    return solution_diagrams.repair(
        condition, ans, solution, result, figure + html, (key,) if key else (), changes
    )
