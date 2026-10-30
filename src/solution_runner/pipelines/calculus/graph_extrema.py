"""Function extrema and derivative sign changes share exact interval selection."""

import re
from dataclasses import dataclass
from fractions import Fraction

from ..equations.linear_system_intervals import Interval, interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import curve_levels, graph_input
from .common import answer
from .graph_stationary import interval, select

_PREFIX = re.compile(
    r"На рисунке изображен график (?P<graph>производной функции f\(x\)|(?:функции )?y=f'\(x\)(?:\s*— производной функции f\(x\))?|(?:функции )?(?:y=)?f\(x\))"
    r"(?:\s*—\s*)?(?:,?\s*определенной на интервале\s*(?P<domain>\([^)]*\)))?\. (?P<request>.+)"
)
_COUNT = re.compile(
    r"Найдите количество точек (?P<target>максимума|минимума|экстремума) функции f\(x\)\s*"
    r"(?:на (?:отрезке|интервале)\s*(?P<span>[\[(].+[\])])|, принадлежащих интервалу\s*(?P<inside>\(.+\)))"
)
_POINT = re.compile(
    r"Найдите точку (?P<target>экстремума|максимума|минимума) функции f\(x\)"
    r"(?:\s*на (?:отрезке|интервале)\s*(?P<span>[\[(].+[\])]))?"
)
_TARGETS = {"максимума": "max", "минимума": "min", "экстремума": "extrema"}


@dataclass(frozen=True)
class Question:
    derivative: bool
    operation: str
    target: str
    domain: Interval | None
    interval: Interval


def parse(text):
    text = text.replace("−", "-").replace("–", "-")
    prefix = _PREFIX.fullmatch(text)
    if not prefix:
        raise UnsupportedCondition(
            "a complete function or derivative graph question is required"
        )
    derivative = "производной" in prefix["graph"] or "f'(x)" in prefix["graph"]
    domain = interval(prefix["domain"]) if prefix["domain"] else None
    request = prefix["request"].removesuffix(".")
    if (
        request == "Найдите сумму точек экстремума функции f(x)"
        and not derivative
        and domain
    ):
        return Question(False, "sum", "extrema", domain, domain)
    counting = _COUNT.fullmatch(request)
    point = _POINT.fullmatch(request)
    if not counting and not point:
        raise UnsupportedCondition("the entire extremum request must be recognized")
    match = counting or point
    span = match["span"]
    if counting:
        span = span or match["inside"]
    selected = interval(span) if span else domain
    if selected is None:
        raise UnsupportedCondition("an explicit selection interval is required")
    return Question(
        derivative,
        "count" if counting else "point",
        _TARGETS[match["target"]],
        domain,
        selected,
    )


def derivative_extrema(entry):
    zeros = entry["zero_points"]
    ends = [
        xy for segment in entry["curve_segments"] for xy in [segment[0], segment[-1]]
    ]
    raw = curve_levels.distinct_points(
        curve_levels.svg_intersections(entry, 0), min(ends)[0], max(ends)[0]
    )
    if len(raw) != len(zeros):
        raise UnsupportedCondition(
            "the derivative zero chart disagrees with the source curve"
        )
    result = []
    previous = None
    for zero, pixel in zip(zeros, raw, strict=True):
        left, right = zero["left_sign"], zero["right_sign"]
        if (
            left not in [-1, 1]
            or right not in [-1, 1]
            or previous is not None
            and previous != left
        ):
            raise UnsupportedCondition(
                "a complete consistent derivative sign chart is required"
            )
        previous = right
        if abs(zero["svg"][0] - pixel[0]) > 0.5:
            raise UnsupportedCondition(
                "a derivative zero has moved in its source curve"
            )
        if "x" in zero:
            expected = (
                entry["svg_origin"][0] + float(Fraction(zero["x"])) * entry["svg_unit"]
            )
            if abs(expected - pixel[0]) > 0.1 * entry["svg_unit"]:
                raise UnsupportedCondition(
                    "the grid abscissa does not match the derivative zero"
                )
        else:
            lower, upper = map(Fraction, zero["x_bounds"])
            actual = (pixel[0] - entry["svg_origin"][0]) / entry["svg_unit"]
            if not float(lower) <= actual <= float(upper):
                raise UnsupportedCondition(
                    "the bounded abscissa does not match the derivative zero"
                )
        if left != right:
            result.append({**zero, "kind": "max" if left > right else "min"})
    return result


def _input(context):
    data = graph_input.read_graph(context)
    question = parse(data[4])
    entry = data[5]
    expected = "derivative" if question.derivative else "f"
    domain = tuple(map(Fraction, entry["domain"])) if entry.get("domain") else None
    stated = (question.domain.lower, question.domain.upper) if question.domain else None
    if entry.get("curve_name") != expected or domain != stated:
        raise UnsupportedCondition(
            "the audited graph role and domain must match the question"
        )
    span = question.interval
    if question.domain and (
        span.lower < question.domain.lower
        or span.upper > question.domain.upper
        or span.lower == question.domain.lower
        and span.lower_closed
        or span.upper == question.domain.upper
        and span.upper_closed
    ):
        raise UnsupportedCondition(
            "the selection interval lies outside the open function domain"
        )
    points = (
        derivative_extrema(entry) if question.derivative else entry["extrema_points"]
    )
    selected = select(points, span, svg_order=True)
    selected = [
        p
        for p in selected
        if question.target == "extrema" or p["kind"] == question.target
    ]
    if question.operation == "point" and (len(selected) != 1 or "x" not in selected[0]):
        raise UnsupportedCondition(
            "the requested extremum must have a unique exact abscissa"
        )
    if question.operation == "sum" and any("x" not in p for p in selected):
        raise UnsupportedCondition(
            "all extremum abscissae must be exactly readable for their sum"
        )
    active = {**entry}
    if entry.get("illustrations"):
        if (
            [span.lower, span.upper]
            != list(map(Fraction, entry["illustration_interval"]))
            or span.lower_closed
            or span.upper_closed
        ):
            raise UnsupportedCondition(
                "the source illustration does not match the requested interval"
            )
        asset = entry["illustrations"].get(question.target)
        if not asset:
            raise UnsupportedCondition("the matching extremum illustration is required")
        active["solution_asset"] = asset
    return data, question, active, selected


def required_assets(context):
    _, _, entry, _ = _input(context)
    return graph_input.requirements(entry)


def _positions(points):
    if not points:
        return r"\varnothing"
    if all("x" in p for p in points):
        return r";\ ".join(answer(p["x"]).replace(",", "{,}") for p in points)
    return r";\ ".join(rf"x_{{{i}}}" for i in range(1, len(points) + 1))


def _sum_line(name, points):
    numbers = [Fraction(p["x"]) for p in points]
    total = sum(numbers, Fraction(0))
    terms = (
        "+".join("(" + answer(x) + ")" if x < 0 else answer(x) for x in numbers) or "0"
    )
    return total, line(name + "=" + terms + "=" + answer(total))


def proof(question, points):
    maxima = [p for p in points if p["kind"] == "max"]
    minima = [p for p in points if p["kind"] == "min"]
    if question.derivative:
        html = "<p>На рисунке изображён график производной. Точки экстремума функции соответствуют смене её знака:</p>"
        if question.target in ["max", "extrema"]:
            html += line(r"f'(x):+\longrightarrow-\quad\Longrightarrow\quad x_{\max}")
        if question.target in ["min", "extrema"]:
            html += line(r"f'(x):-\longrightarrow+\quad\Longrightarrow\quad x_{\min}")
    else:
        html = "<p>Точка максимума соответствует переходу функции от возрастания к убыванию, а точка минимума — от убывания к возрастанию.</p>"
        if question.target in ["max", "extrema"]:
            html += line(
                r"f:\nearrow\ \longrightarrow\ \searrow\quad\Longrightarrow\quad x_{\max}"
            )
        if question.target in ["min", "extrema"]:
            html += line(
                r"f:\searrow\ \longrightarrow\ \nearrow\quad\Longrightarrow\quad x_{\min}"
            )
    html += "<p>Учитываем только подходящие точки заданного промежутка:</p>" + line(
        r"x\in " + interval_latex(question.interval)
    )
    for kind, selected in [("max", maxima), ("min", minima)]:
        if question.target not in [kind, "extrema"]:
            continue
        if question.derivative and any("x" not in point for point in selected):
            html += line("N_{\\" + kind + "}=" + str(len(selected)))
        else:
            html += line("x_{\\" + kind + "}:\\ " + _positions(selected))
    if question.operation == "sum":
        sm, first = _sum_line(r"S_{\max}", maxima)
        sn, second = _sum_line(r"S_{\min}", minima)
        html += (
            "<p>Сложим абсциссы максимумов и минимумов:</p>"
            + first
            + second
            + line("S=" + answer(sm) + "+(" + answer(sn) + ")=" + answer(sm + sn))
        )
        return answer(sm + sn), html
    if question.operation == "point":
        result = answer(points[0]["x"])
        html += "<p>Подходящая точка одна, её абсцисса:</p>" + line("x=" + result)
        return result, html
    html += "<p>Подсчитаем найденные точки:</p>"
    if question.target == "extrema":
        html += line(
            "N=" + str(len(maxima)) + "+" + str(len(minima)) + "=" + str(len(points))
        )
    else:
        html += line("N=" + str(len(points)))
    return str(len(points)), html


def build_context_repair_plan(context, *, condition_asset_bytes=None):
    data, question, entry, points = _input(context)
    content, condition, ans, solution, _, original, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(question, points)
    current = entry.get("solution_asset")
    current_id = current["source_id"] if current else None
    obsolete = {a["source_id"] for a in original.get("illustrations", {}).values()} - {
        current_id
    }
    removed = [
        {"transformation_target_id": "asset:" + a["asset_key"], "operation": "remove"}
        for a in content["assets"]
        if a["asset_id"] in obsolete
    ]
    content = {
        **content,
        "assets": [a for a in content["assets"] if a["asset_id"] not in obsolete],
    }
    figure, key, changes = graph_input.figure(content, entry)
    return solution_diagrams.repair(
        condition,
        ans,
        solution,
        result,
        figure + html,
        (key,) if key else (),
        tuple(removed) + tuple(changes),
    )
