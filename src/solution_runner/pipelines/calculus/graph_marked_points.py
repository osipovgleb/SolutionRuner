"""Signs and tangent comparisons at labelled points of one reviewed graph."""

import hashlib
import io
import re
from dataclasses import dataclass
from fractions import Fraction
from html import escape
from itertools import pairwise
from math import isfinite
from random import Random
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image

from ..equations.linear_system_intervals import Interval
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import (
    curve_levels,
    graph_condition_layout,
    graph_input,
    marked_curve_render,
    tangent_native,
)
from .common import answer
from .graph_reading import NOTE
from .graph_stationary import interval

_GRAPH = re.compile(
    r"На рисунке изображен график (?P<curve>(?:функции )?y=f'\(x\)(?:— )?производной функции f\(x\)|(?:дифференцируемой )?функции y=f\(x\))(?P<tail>.+)"
)
_MARKERS = re.compile(
    r"(?:\. На оси абсцисс отмечен[оы]|(?:— )?и(?: отмечены)?) (?P<count>\w+) точек(?: на оси абсцисс)?:? (?P<points>.+?)\. (?P<request>.+)"
)
_DOMAIN = re.compile(
    r", определенной на интервале(?P<domain>\([^)]*\))\. Сколько из отмеченных точек (?P<points>.+?) принадлежат промежуткам (?P<direction>убывания|возрастания) функции\?"
)
_COMPARE = re.compile(
    r"(?:и отмечены точки|\. На оси абсцисс отмечены точки) (?P<points>.+?)\. В какой из этих точек значение производной (?P<target>наибольшее|наименьшее)\? В ответе укажите эту точку\."
)
_SIGN = re.compile(
    r"В скольких из этих точек производная функции f\(x\)(?P<sign>положительна|отрицательна)\?"
)
_MONOTONIC = re.compile(
    r"(?:В скольких из этих точек функция f\(x\)(?P<verb>возрастает|убывает)|Сколько из (?:этих|отмеченных) точек (?:лежит на|принадлежит) промежутк(?:ах|ам) (?P<direction>возрастания|убывания) функции f\(x\))\?"
)
_ALL = re.compile(
    r"Среди этих точек найдите все точки, в которых производная функции (?:y=)?f\(x\)(?P<sign>отрицательна|положительна)\. В ответе укажите количество найденных точек\."
)
_COUNTS = {
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
}
_NS = "http://www.w3.org/2000/svg"
_GUIDE_KEY = "marked_point_classification"
_SIGN_CHART_KEY = "marked_derivative_signs"
_SLOPE_CHART_KEY = "marked_function_slope_chart"
_COLOURED_CURVE_KEY = "marked_monotonic_curve"
_CATALOG_CURVE_KEY = "marked_smoothed_monotonic_curve"
_SIGNED_CURVE_KEY = "marked_function_growth_and_decline"
_TANGENTS_KEY = "uniform_marked_tangents"
_PREVIOUS_TANGENT_KEYS = {
    "marked_tangent_comparison",
    "marked_all_tangents",
    "styled_function_tangents",
}
_SLOPE_COLORS = {-1: "#218BCC", 0: "#15803d", 1: "#b42318"}
_MONOTONICITY_RULE = (
    "<p><b>Правило:</b> Если производная положительна, то функция возрастает. "
    "Если производная отрицательна, то функция убывает.</p>"
)
ET.register_namespace("", _NS)


@dataclass(frozen=True)
class Question:
    derivative: bool
    operation: str
    labels: tuple
    sign: int = 0
    target: str = ""
    domain: Interval | None = None


def labels(text):
    parts = [s.strip() for s in text.split(",")]
    if "..." in parts:
        if (
            len(parts) not in [4, 5]
            or parts.count("...") != 1
            or parts[-2] != "..."
            or parts[:-2] not in [["x_{1}", "x_{2}"], ["x_{1}", "x_{2}", "x_{3}"]]
        ):
            raise UnsupportedCondition(
                "only a consecutive marked-point ellipsis is supported"
            )
        final = re.fullmatch(r"x_\{(\d+)\}", parts[-1])
        if not final or not len(parts) <= int(final[1]) <= 12:
            raise UnsupportedCondition("an explicit final marker is required")
        return tuple(range(1, int(final[1]) + 1))
    result = []
    for part in parts:
        match = re.fullmatch(r"x_\{(\d+)\}", part)
        if not match:
            raise UnsupportedCondition("every marked-point label must be recognized")
        result.append(int(match[1]))
    if result != list(range(1, len(result) + 1)):
        raise UnsupportedCondition(
            "all consecutive markers must be listed exactly once"
        )
    return tuple(result)


def parse(text):
    text = (
        text.replace("−", "-")
        .replace("–", "-")
        .replace("…", "...")
        .replace(r"\dots", "...")
        .replace(r"\,", "")
    )
    text = re.sub(r"x\s*_\{?(\d+)\}?", r"x_{\1}", text)
    text = text.replace("изображен графи функции", "изображен график функции")
    if text == (
        "На рисунке изображен график функции и шесть точек на оси абсцисс. "
        "В скольких из этих точек производная функции отрицательна?"
    ):
        return Question(False, "strict", (1, 2, 3, 4, 5, 6), -1)
    match = _GRAPH.fullmatch(text)
    if not match:
        raise UnsupportedCondition("a complete labelled-graph question is required")
    derivative = "производной" in match["curve"]
    tail = match["tail"]
    comparison = _COMPARE.fullmatch(tail)
    if comparison and not derivative:
        numbers = comparison["points"].split(", ")
        if any(not re.fullmatch(r"-?\d+", n) for n in numbers):
            raise UnsupportedCondition(
                "all comparison abscissae must be explicit integers"
            )
        points = tuple(map(int, numbers))
        if len(points) != len(set(points)) or len(points) < 2:
            raise UnsupportedCondition("distinct comparison points are required")
        return Question(False, "compare", points, target=comparison["target"])
    domain = _DOMAIN.fullmatch(tail)
    if domain and not derivative:
        return Question(
            False,
            "monotonic",
            labels(domain["points"]),
            1 if domain["direction"] == "возрастания" else -1,
            domain=interval(domain["domain"]),
        )
    marked = _MARKERS.fullmatch(tail)
    if not marked:
        raise UnsupportedCondition(
            "the entire marked-point statement must be recognized"
        )
    points = labels(marked["points"])
    if _COUNTS.get(marked["count"]) != len(points):
        raise UnsupportedCondition("the stated marker count and list disagree")
    request = marked["request"]
    strict = _SIGN.fullmatch(request) or _ALL.fullmatch(request)
    if strict:
        return Question(
            derivative, "strict", points, 1 if strict["sign"] == "положительна" else -1
        )
    monotonic = _MONOTONIC.fullmatch(request)
    if monotonic:
        positive = (
            monotonic["verb"] == "возрастает" or monotonic["direction"] == "возрастания"
        )
        return Question(derivative, "monotonic", points, 1 if positive else -1)
    raise UnsupportedCondition("the entire marked-point request must be recognized")


def validate_stationary(entry, point, low, high):
    if max(abs(low), abs(high)) > 0.1:
        raise UnsupportedCondition("the reviewed horizontal tangent has changed")
    if "adjacent_signs" in point:
        for offset, sign in zip([-2, 2], point["adjacent_signs"], strict=True):
            if sign not in [-1, 1] or any(
                slope * sign <= 0.001
                for _, slope in curve_levels.at_abscissa(
                    entry, point["svg"][0] + offset
                )
            ):
                raise UnsupportedCondition(
                    "the adjacent monotonicity signs disagree with the source curve"
                )


def readings(entry):
    points = entry["markers"]
    if any(a["svg"][0] >= b["svg"][0] for a, b in pairwise(points)):
        raise UnsupportedCondition("the marked abscissae must be strictly ordered")
    result = []
    for point in points:
        samples = curve_levels.at_abscissa(entry, point["svg"][0])
        if any(abs(y - point["svg"][1]) > 1.5 for y, _ in samples):
            raise UnsupportedCondition("the marked point has moved from its curve")
        low, high = min(s for _, s in samples), max(s for _, s in samples)
        if point.get("stationary"):
            validate_stationary(entry, point, low, high)
            low = high = 0
        result.append({**point, "slopes": (low, high)})
    return result


def raster_gray(source):
    with Image.open(io.BytesIO(source)) as image:
        rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    return Image.alpha_composite(background, rgba).convert("L")


def raster_readings(entry, source, question):
    if not source.startswith(b"\x89PNG\r\n\x1a\n"):
        raise UnsupportedCondition("reviewed raster markers require a PNG")
    gray = raster_gray(source)
    axis = entry["svg_origin"][1]
    if not 0 <= axis < gray.height:
        raise UnsupportedCondition("the reviewed horizontal axis is outside the image")
    markers = entry["markers"]
    if any(a["svg"][0] >= b["svg"][0] for a, b in pairwise(markers)):
        raise UnsupportedCondition("the marked abscissae must be strictly ordered")
    for point in markers:
        x, y = map(round, point["svg"])
        if (
            not (1 <= x < gray.width - 1 and 1 <= y < gray.height - 1)
            or gray.crop((x - 1, y - 1, x + 2, y + 2)).getextrema()[0] > 145
            or question.derivative
            and abs(y - axis) < 3
        ):
            raise UnsupportedCondition("a reviewed raster marker is unresolved")
    if question.derivative:
        return markers
    result = []
    for point in markers:
        if question.operation == "compare":
            bounds = point.get("slope_bounds", ())
            if (
                len(bounds) != 2
                or not all(
                    isinstance(slope, (float, int)) and isfinite(slope)
                    for slope in bounds
                )
                or bounds[0] > bounds[1]
            ):
                raise UnsupportedCondition("the raster tangent slope needs review")
            result.append({**point, "slopes": tuple(bounds)})
            continue
        sign = point.get("slope_sign")
        if sign not in (-1, 0, 1):
            raise UnsupportedCondition("the raster tangent sign needs review")
        result.append({**point, "slopes": (sign, sign)})
    return result


def raster_outline(source):
    return outline_ink(np.asarray(raster_gray(source)) <= 150)


def outline_ink(ink):
    height, width = ink.shape
    mask = ink.astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    paths = []
    for contour in contours:
        outline = cv2.approxPolyDP(contour, 0.65, True).reshape(-1, 2)
        if len(outline) >= 3:
            paths.append("M" + " L".join(f"{x},{y}" for x, y in outline) + "Z")
    root = ET.Element(
        "{" + _NS + "}svg",
        viewBox=f"0 0 {width} {height}",
        width=str(width),
        height=str(height),
    )
    ET.SubElement(
        root,
        "{" + _NS + "}path",
        d=" ".join(paths),
        fill="#000000",
        attrib={"fill-rule": "evenodd"},
    )
    return root


def point_sign(point, entry, derivative):
    if derivative:
        delta = entry["svg_origin"][1] - point["svg"][1]
        if point.get("zero"):
            if abs(delta) > 1:
                raise UnsupportedCondition("the marked derivative zero has changed")
            return 0
        if abs(delta) < 1:
            raise UnsupportedCondition(
                "the derivative sign is not resolved at this marker"
            )
        return 1 if delta > 0 else -1
    low, high = point["slopes"]
    if low == high == 0:
        return 0
    if low > 0.08:
        return 1
    if high < -0.08:
        return -1
    raise UnsupportedCondition("a near-horizontal marked tangent needs review")


def select(question, entry, points):
    if question.operation == "compare":
        maximum = question.target == "наибольшее"
        winners = [
            p
            for p in points
            if all(
                p is q
                or (
                    p["slopes"][0] > q["slopes"][1] + 0.1
                    if maximum
                    else p["slopes"][1] < q["slopes"][0] - 0.1
                )
                for q in points
            )
        ]
        if len(winners) != 1:
            raise UnsupportedCondition(
                "the marked tangents do not prove a unique comparison"
            )
        return winners
    result = []
    for point in points:
        sign = point_sign(point, entry, question.derivative)
        if sign == question.sign:
            result.append(point)
        elif sign == 0 and question.operation == "monotonic":
            if question.sign in point.get("adjacent_signs", []):
                result.append(point)
            elif not point.get("adjacent_signs"):
                raise UnsupportedCondition(
                    "a zero needs its adjacent monotonicity signs"
                )
    return result


def _reviewed_raster(entry):
    reference_id = entry["raster_reference_asset"]
    reference = graph_input.EVIDENCE[reference_id]
    source = (graph_input.ASSETS / (reference_id + reference["extension"])).read_bytes()
    if hashlib.sha256(source).hexdigest() != reference["sha256"]:
        raise UnsupportedCondition("the original raster has changed")
    return reference, source


def _input(context):
    data = graph_input.read_graph(context)
    entry = data[5]
    question = parse(data[4])
    domain = (question.domain.lower, question.domain.upper) if question.domain else None
    expected = (
        tuple(map(Fraction, entry["marked_domain"]))
        if entry.get("marked_domain")
        else None
    )
    if (
        entry["curve_name"] != ("derivative" if question.derivative else "f")
        or domain != expected
    ):
        raise UnsupportedCondition(
            "the reviewed graph role and domain must match the question"
        )
    if entry.get("raster_reference_asset"):
        reference, raw = _reviewed_raster(entry)
        points = raster_readings(reference, raw, question)
    elif entry.get("extension") == ".png":
        points = raster_readings(entry, data[6], question)
    else:
        points = readings(entry)
    if tuple(p["label"] for p in points) != question.labels:
        raise UnsupportedCondition(
            "the labelled points do not match the reviewed diagram"
        )
    if (
        entry.get("illustration_target")
        and question.target != entry["illustration_target"]
    ):
        raise UnsupportedCondition(
            "the source tangent illustration does not match the request"
        )
    return data, question, points, select(question, entry, points)


def position(point, question):
    return (
        answer(point["label"])
        if question.operation == "compare"
        else rf"x_{{{point['label']}}}"
    )


def proof(question, entry, points, selected):
    if question.operation == "compare":
        winner = selected[0]
        label = position(winner, question)
        by_sign = {sign: [] for sign in (-1, 0, 1)}
        magnitudes = {}
        for point in points:
            low, high = point["slopes"]
            sign = 1 if low > 0 else -1 if high < 0 else 0
            x = position(point, question)
            by_sign[sign].append(x)
            magnitudes[x] = abs(low + high) / 2

        def inline(formula):
            return f'<span data-inline-latex="{escape(formula)}"></span>'

        html = ""
        for sign, singular, plural, relation in [
            (-1, "убывает", "убывают", "<"),
            (1, "возрастает", "возрастают", ">"),
        ]:
            positions = by_sign[sign]
            if positions:
                subject = "Касательная" if len(positions) == 1 else "Касательные"
                verb = singular if len(positions) == 1 else plural
                formulas = r",\quad ".join(f"f'({x}){relation}0" for x in positions)
                html += f"<p>{subject} {verb}, поэтому {inline(formulas)}.</p>"
        if by_sign[0]:
            values = r",\quad ".join(f"f'({x})" for x in by_sign[0])
            html += f"<p>Почти горизонтальные касательные дают значения {inline(values)}, близкие к нулю.</p>"

        maximum = question.target == "наибольшее"
        direction = 1 if maximum else -1
        candidates = by_sign[direction]
        if label in candidates and len(candidates) > 1:
            # Stable examples keep the prepared and applied solutions identical.
            rng = Random(repr(magnitudes))
            ranks = sorted(candidates, key=magnitudes.__getitem__)
            numbers = sorted(rng.sample(range(1, 13), len(ranks)))
            example = dict(zip(ranks, numbers, strict=True))
            html += (
                "<p>"
                + (
                    "Сравниваем модули отрицательных производных. "
                    if not maximum
                    else ""
                )
                + "У более крутой касательной численное значение больше, например:</p>"
            )
            html += "".join(
                line(f"f'({x})={direction * example[x]}") for x in candidates
            )
        elif label not in candidates:
            html += f"<p>Сравнение наклонов даёт {question.target} значение производной при {inline('x=' + label)}.</p>"
        html += f"<p>Поэтому выбираем {inline(label)}.</p>"
        return label, html
    count = len(selected)
    if _signed_curve(entry):
        requested = "красные" if question.sign > 0 else "зелёные"
        legend = (
            "<p>Красным показано возрастание, зелёным — убывание. "
            f"Считаем {requested} точки.</p>"
        )
        if any(point_sign(point, entry, False) == 0 for point in points):
            labels = [
                position(point, question)
                for point in selected
                if point_sign(point, entry, False) == 0
            ]
            legend = legend.replace(
                f"Считаем {requested} точки.",
                "Серым отмечены точки с горизонтальной касательной. "
                f"Считаем {requested} точки"
                + (
                    f' и <span data-inline-latex="{escape(", ".join(labels))}"></span>'
                    if labels
                    else ""
                )
                + ".",
            )
        return str(count), legend + line("N=" + str(count))
    legend = (
        "<p>В синих точках функция убывает, зелёные точки показывают экстремумы, "
        "в красных точках функция возрастает.</p>"
        if entry.get("point_colors_by_slope")
        else "<p>Подходящие точки отмечены зелёным, остальные — красным.</p>"
    )
    return str(count), legend + line("N=" + str(count))


def render_svg(source, entry, points):
    root = (
        marked_curve_render.tangent_raster(
            np.asarray(raster_gray(source)) <= 150, entry["svg_origin"], points
        )
        if entry.get("extension") == ".png"
        else ET.fromstring(source)
    )
    xmin, ymin, width, height = map(float, root.get("viewBox").split())
    marked_curve_render.display_size(root)
    for node in root.iter("{" + _NS + "}text"):
        if (node.text or "").strip() in ["−", "–", "-"]:
            node.set("font-family", "Times New Roman,serif")
    group = ET.Element("{" + _NS + "}g", {"data-runner-diagram": "tangent_comparison"})
    root.append(group)
    for point in points:
        low, high = point["slopes"]
        slope = (low + high) / 2
        length = width * 0.18
        dx = length / (1 + slope * slope) ** 0.5
        color = (
            marked_curve_render.RED
            if low > 0
            else "#7e22ce"
            if high < 0
            else "#6b7280"
        )
        x, y = point["svg"]
        left, right = point.get("tangent_lengths", [1, 1])
        a, b = -dx * left, dx * right
        for coordinate, delta, lower, upper in [
            (x, 1, xmin + 2, xmin + width - 2),
            (y, -slope, ymin + 2, ymin + height - 2),
        ]:
            if delta:
                limits = sorted(
                    [(lower - coordinate) / delta, (upper - coordinate) / delta]
                )
                a = max(a, limits[0])
                b = min(b, limits[1])
        ET.SubElement(
            group,
            "{" + _NS + "}line",
            {
                "x1": str(x + a),
                "y1": str(y - slope * a),
                "x2": str(x + b),
                "y2": str(y - slope * b),
                "stroke": color,
                "stroke-width": str(width * 0.006),
                "stroke-dasharray": f"{width * 0.018:.3f} {width * 0.009:.3f}",
                "stroke-linecap": "round",
            },
        )
    for point in points:
        x, y = point["svg"]
        ET.SubElement(
            group,
            "{" + _NS + "}circle",
            cx=str(x),
            cy=str(y),
            r=str(width * 0.006),
            fill="#334155",
            stroke="white",
            **{"stroke-width": str(width * 0.002)},
        )
    return ET.tostring(root, encoding="unicode")


def marked_sign_chart(root, entry, question, points):
    from . import monotonic_sum_render
    from .monotonic_sum_input import Graph

    xmin, _, width, _ = map(float, root.get("viewBox").split())
    origin = entry.get("svg_origin") or (0, 0)
    oy = origin[1]
    if not question.derivative:
        chart = entry["function_sign_chart"]
        cuts = chart["turns"]
        limits = [chart["left"], *(x for x, _ in cuts), chart["right"]]
        bands = [
            (a, b, chart["initial"] * (-1) ** i)
            for i, (a, b) in enumerate(pairwise(limits))
        ]
    elif entry.get("extension") == ".png":
        cuts = [(x, oy) for x in entry["axis_crossings"]]
        left, right = xmin + width * 0.015, xmin + width * 0.985
        limits = [left, *(x for x, _ in cuts), right]
        if any(a >= b for a, b in pairwise(limits)):
            raise UnsupportedCondition("the reviewed crossings must be ordered")
        reference = points[0]
        reference_sign = point_sign(reference, entry, True)
        before = sum(x < reference["svg"][0] for x, _ in cuts)
        initial = reference_sign * (-1) ** before
        bands = [
            (a, b, initial * (-1) ** i) for i, (a, b) in enumerate(pairwise(limits))
        ]
    else:
        ends = [point[0] for segment in entry["curve_segments"] for point in segment]
        left, right = min(ends), max(ends)
        cuts = curve_levels.distinct_points(
            curve_levels.svg_intersections({**entry, "svg_unit": 1}, 0), left, right
        )
        limits = [left, *(x for x, _ in cuts), right]
        bands = []
        for a, b in pairwise(limits):
            ordinates = curve_levels.at_abscissa(entry, (a + b) / 2)
            signs = {1 if y < oy else -1 for y, _ in ordinates}
            if len(signs) != 1:
                raise UnsupportedCondition("the source must resolve each sign interval")
            bands.append((a, b, signs.pop()))
    for point in points:
        x, _ = point["svg"]
        sign = point_sign(point, entry, question.derivative)
        if sign and not any(
            a <= x <= b and sign == band_sign for a, b, band_sign in bands
        ):
            raise UnsupportedCondition("a sign interval disagrees with a marked point")
    unit = width * 0.052
    graph = Graph(
        question,
        {},
        {},
        ET.tostring(root),
        None,
        {**entry, "svg_origin": origin, "svg_unit": unit},
        tuple(cuts),
        tuple(bands),
        (),
    )
    return monotonic_sum_render.render(graph, stroke_scale=unit / 20)


def _signed_curve(entry):
    return any(
        entry.get(key)
        for key in (
            "catalog_function_style",
            "color_function_curve",
            "color_marked_monotonicity",
        )
    )


def _solution_figure(source, entry, question, points, selected):
    if question.operation == "compare":
        return _TANGENTS_KEY, render_svg(source, entry, points)
    if _signed_curve(entry) and entry.get("raster_reference_asset"):
        raster, raw = _reviewed_raster(entry)
        points = [
            {**point, "sign": point_sign(point, raster, False)} for point in points
        ]
        root = marked_curve_render.tangent_raster(
            np.asarray(raster_gray(raw)) <= 150,
            raster["svg_origin"],
            points,
            course_style=True,
            indexed=True,
            function_chart=raster["function_sign_chart"],
            selected=selected,
            signed=True,
        )
        return _SIGNED_CURVE_KEY, ET.tostring(root, encoding="unicode")
    if entry.get("raster_reference_asset"):
        entry, source = _reviewed_raster(entry)
    if _signed_curve(entry):
        points = [
            {**point, "sign": point_sign(point, entry, False)} for point in points
        ]
        if not entry.get("function_sign_chart"):
            entry = {
                **entry,
                "function_sign_chart": marked_curve_render.chart_from_curve(entry),
            }
        return _SIGNED_CURVE_KEY, marked_curve_render.render(
            source,
            entry,
            points,
            selected,
            raster_gray=raster_gray,
            outline=outline_ink,
            catalog_style=True,
            signed=True,
        )
    if entry.get("solution_asset"):
        return None, None
    if entry.get("extension") == ".png":
        root = raster_outline(source)
    else:
        root = ET.fromstring(source)
    if any(
        node.get("style") or node.tag == tangent_native.NS + "style"
        for node in root.iter()
    ):
        root = ET.fromstring(tangent_native.presentation(source))
    width = float(root.get("viewBox").split()[2])
    group = ET.SubElement(
        root, tangent_native.NS + "g", {"data-runner-diagram": "selected_markers"}
    )
    origin = entry.get("svg_origin")
    axis = origin[1] if origin else None
    for point in points:
        x, y = point["svg"]
        if entry.get("point_colors_by_slope"):
            color = _SLOPE_COLORS[point_sign(point, entry, question.derivative)]
        else:
            color = "#15803d" if point in selected else "#b42318"
        if axis is not None and abs(y - axis) > width * 0.01:
            ET.SubElement(
                group,
                tangent_native.NS + "line",
                x1=str(x),
                x2=str(x),
                y1=str(axis),
                y2=str(y),
                stroke=color,
                **{"stroke-width": "1", "stroke-dasharray": "3 2"},
            )
        ET.SubElement(
            group,
            tangent_native.NS + "circle",
            cx=str(x),
            cy=str(y),
            r=str(width * 0.009),
            fill=color,
            stroke="white",
            **{"stroke-width": str(width * 0.002)},
        )
    if entry.get("point_colors_by_slope"):
        return _SLOPE_CHART_KEY, marked_sign_chart(root, entry, question, points)
    if question.derivative or entry.get("function_sign_chart"):
        key = _SIGN_CHART_KEY if question.derivative else _GUIDE_KEY
        return key, marked_sign_chart(root, entry, question, points)
    return _GUIDE_KEY, ET.tostring(root, encoding="unicode")


def required_assets(context):
    data, question, _, _ = _input(context)
    return () if question.operation == "compare" else graph_input.requirements(data[5])


def diagram_specs(context):
    data, question, points, selected = _input(context)
    key, svg = _solution_figure(data[6], data[5], question, points, selected)
    return (solution_diagrams.spec(key, svg),) if key else ()


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question, points, selected = _input(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    proof_entry = (
        graph_input.EVIDENCE[entry["raster_reference_asset"]]
        if entry.get("catalog_function_style") and entry.get("raster_reference_asset")
        else entry
    )
    result, html = proof(question, proof_entry, points, selected)
    key, svg = _solution_figure(source, entry, question, points, selected)
    obsolete = ()
    if key in (
        _GUIDE_KEY,
        _SIGN_CHART_KEY,
        _SLOPE_CHART_KEY,
        _COLOURED_CURVE_KEY,
        _CATALOG_CURVE_KEY,
        _SIGNED_CURVE_KEY,
        _TANGENTS_KEY,
    ):
        prior_solution = entry.get("solution_asset") if key == _TANGENTS_KEY else None
        entry = {
            **entry,
            "diagram_key": key,
            "solution_alt": "График с выделенными точками",
        }
        if prior_solution:
            entry = {**entry, "solution_asset": None}
        previous_keys = {"selected_markers", "marked_point_guides"}
        if key == _TANGENTS_KEY:
            previous_keys.update(_PREVIOUS_TANGENT_KEYS)
        if key in (_COLOURED_CURVE_KEY, _CATALOG_CURVE_KEY, _SIGNED_CURVE_KEY):
            previous_keys.add(_GUIDE_KEY)
        if key in (_CATALOG_CURVE_KEY, _SIGNED_CURVE_KEY):
            previous_keys.add(_COLOURED_CURVE_KEY)
        if key == _SIGNED_CURVE_KEY:
            previous_keys.add(_CATALOG_CURVE_KEY)
        if key != _SIGN_CHART_KEY:
            previous_keys.add(_SIGN_CHART_KEY)
        if key == _SLOPE_CHART_KEY:
            previous_keys.add(_GUIDE_KEY)
        previous_solution_asset_id = (
            prior_solution["source_id"]
            if prior_solution
            else entry.get("previous_solution_asset_id")
        )
        previous_keys.update(
            asset["asset_key"]
            for asset in content["assets"]
            if asset["asset_id"] == previous_solution_asset_id
        )
        previous_keys.intersection_update((solution or {}).get("asset_keys", ()))
        previous_keys.difference_update(condition.get("asset_keys", ()))
        if previous_keys:
            obsolete = tuple(
                {"transformation_target_id": "asset:" + k, "operation": "remove"}
                for k in sorted(previous_keys)
            )
            content = {
                **content,
                "assets": [
                    asset
                    for asset in content["assets"]
                    if asset["asset_key"] not in previous_keys
                ],
            }
    figure, key, changes = graph_input.figure(
        content,
        entry,
        svg=svg,
        generated=generated_solution_assets,
        replace_generated=key in (_SIGNED_CURVE_KEY, _TANGENTS_KEY),
    )
    plan = solution_diagrams.repair(
        condition,
        ans,
        solution,
        result,
        (_MONOTONICITY_RULE if question.operation != "compare" else "")
        + figure
        + html
        + (NOTE if question.operation != "compare" else ""),
        (key,) if key else (),
        obsolete + tuple(changes),
    )
    return graph_condition_layout.apply_layout(
        plan,
        context,
        image_width=marked_curve_render.DISPLAY_WIDTH
        if key in (_SIGNED_CURVE_KEY, _TANGENTS_KEY)
        else None,
    )
