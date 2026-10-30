"""Signs and tangent comparisons at labelled points of one reviewed graph."""

import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from xml.etree import ElementTree as ET

from ..equations.linear_system_intervals import Interval
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import curve_levels, graph_input
from .common import answer
from .graph_stationary import interval

_GRAPH = re.compile(
    r"На рисунке изображен график (?P<curve>(?:функции )?y=f'\(x\)(?:— )?производной функции f\(x\)|(?:дифференцируемой )?функции y=f\(x\))(?P<tail>.+)"
)
_MARKERS = re.compile(
    r"(?:\. На оси абсцисс отмечен[оы]|(?:— )?и(?: отмечены)?) (?P<count>\w+) точек(?: на оси абсцисс)?: (?P<points>.+?)\. (?P<request>.+)"
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
    r"Среди этих точек найдите все точки, в которых производная функции f\(x\)(?P<sign>отрицательна|положительна)\. В ответе укажите количество найденных точек\."
)
_COUNTS = {
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "одиннадцать": 11,
    "двенадцать": 12,
}
_NS = "http://www.w3.org/2000/svg"


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
        html = (
            "<p>Значение производной в точке касания равно угловому коэффициенту касательной, то есть тангенсу её угла наклона к оси абсцисс:</p>"
            + line(r"f'(x)=k=\tan\alpha")
        )
        html += (
            "<p>Сравним наклоны касательных в отмеченных точках. По рисунку касательная в искомой точке имеет "
            + question.target
            + " значение углового коэффициента:</p>"
        )
        for point in points:
            if point is not winner:
                html += line(
                    "f'("
                    + label
                    + ")"
                    + (r">" if question.target == "наибольшее" else "<")
                    + "f'("
                    + position(point, question)
                    + ")"
                )
        html += "<p>Следовательно, требуемая абсцисса:</p>" + line("x=" + label)
        return label, html
    relation = ">" if question.sign > 0 else "<"
    html = (
        "<p>"
        + (
            "На рисунке дана производная. Определяем её знак по положению графика относительно оси абсцисс."
            if question.derivative
            else "Положительной производной соответствуют участки возрастания функции, отрицательной — участки убывания."
        )
        + "</p>"
    )
    html += line(r"f'(x)>0\ \Longrightarrow\ f\nearrow") + line(
        r"f'(x)<0\ \Longrightarrow\ f\searrow"
    )
    zero = [p for p in points if point_sign(p, entry, question.derivative) == 0]
    if zero:
        html += (
            "<p>В точках с горизонтальной касательной производная равна нулю:</p>"
            + line("x\\in\\{" + ";".join(position(p, question) for p in zero) + "\\}")
        )
    if entry.get("classify_all_signs"):
        positive = [p for p in points if point_sign(p, entry, question.derivative) > 0]
        html += "<p>В точках, выделенных синим, функция возрастает, её производная положительна:</p>"
        html += line(
            r"f'(x)>0,\quad x\in\{"
            + ";".join(position(p, question) for p in positive)
            + r"\}"
        )
        html += "<p>В точках, выделенных зелёным, функция убывает, её производная отрицательна.</p>"
    html += "<p>Выбираем отмеченные точки, отвечающие вопросу:</p>" + line(
        "x\\in\\{" + ";".join(position(p, question) for p in selected) + "\\}"
    )
    for point in selected:
        sign = point_sign(point, entry, question.derivative)
        html += line(
            "f'(" + position(point, question) + ")" + (relation + "0" if sign else "=0")
        )
    html += "<p>Подсчитаем выбранные точки:</p>" + line("N=" + str(len(selected)))
    return str(len(selected)), html


def render_svg(source, question, points, selected):
    root = ET.fromstring(source)
    xmin, ymin, width, height = map(float, root.get("viewBox").split())
    for node in root.iter("{" + _NS + "}text"):
        if (node.text or "").strip() in ["−", "–", "-"]:
            node.set("font-family", "Times New Roman,serif")
    group = ET.Element("{" + _NS + "}g", {"data-runner-diagram": "tangent_comparison"})
    root.insert(0, group)
    maximum = question.target == "наибольшее"
    for point in points:
        low, high = point["slopes"]
        if point not in selected and (low <= 0.1 if maximum else high >= -0.1):
            continue
        slope = (low + high) / 2
        dx = min(width * 0.15, 45) / (1 + slope * slope) ** 0.5
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
                "stroke": "#218BCC",
                "stroke-width": "1.25",
            },
        )
    return ET.tostring(root, encoding="unicode")


def required_assets(context):
    data, _, _, _ = _input(context)
    return graph_input.requirements(data[5])


def diagram_specs(context):
    data, question, points, selected = _input(context)
    entry = data[5]
    return (
        (
            solution_diagrams.spec(
                entry["diagram_key"], render_svg(data[6], question, points, selected)
            ),
        )
        if entry.get("draw_tangents")
        else ()
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question, points, selected = _input(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(question, entry, points, selected)
    svg = (
        render_svg(source, question, points, selected)
        if entry.get("draw_tangents")
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated_solution_assets
    )
    return solution_diagrams.repair(
        condition, ans, solution, result, figure + html, (key,) if key else (), changes
    )
