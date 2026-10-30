"""A tangent parallel to y=kx+b is found on the derivative graph at level k."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction

import sympy as sp

from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import curve_levels, graph_input
from .common import X, answer, polynomial
from .graph_stationary import interval

_PREFIX = re.compile(
    r"На рисунке изображен график (?:производной функции f\(x\)|y=f'\(x\)\s*— производной функции f\(x\))"
    r"(?:,? определенной на (?:интервале|отрезке)(?P<domain>\([^)]*\)))?\. (?P<request>.+)"
)
_COUNT = re.compile(
    r"Найдите количество точек, в которых касательная к графику функции f\(x\)\s*параллельна прямой y=(?P<line>.+?) или совпадает с ней\."
)
_ROOT = re.compile(
    r"Найдите абсциссу точки(?: графика y=f\(x\))?, в которой касательная к графику "
    r"(?:функции y=f\(x\)|y=f\(x\)|функции)\s*параллельна "
    r"(?:прямой y=(?P<line>.+?)|(?P<axis>оси абсцисс)) или совпадает с ней\."
)
_NS = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class Question:
    count: bool
    slope: sp.Expr
    comparison: sp.Expr | None
    domain: tuple | None


def parse(text):
    text = text.replace("−", "-").replace("–", "-")
    prefix = _PREFIX.fullmatch(text)
    if not prefix:
        raise UnsupportedCondition("the graph must explicitly depict the derivative")
    request = prefix["request"]
    match = _COUNT.fullmatch(request)
    counting = match is not None
    if match is None:
        match = _ROOT.fullmatch(request)
    if match is None:
        raise UnsupportedCondition("unsupported complete derivative-level request")
    comparison = None if match["line"] is None else polynomial(match["line"], X)
    if comparison is not None and sp.Poly(comparison, X).degree() > 1:
        raise UnsupportedCondition("the comparison must be a straight line")
    slope = sp.S.Zero if comparison is None else sp.diff(comparison, X)
    domain = interval(prefix["domain"]) if prefix["domain"] else None
    return Question(
        counting, slope, comparison, (domain.lower, domain.upper) if domain else None
    )


def _input(context):
    data = graph_input.read_graph(context)
    question = parse(data[4])
    entry = data[5]
    domain = tuple(map(Fraction, entry["domain"])) if entry.get("domain") else None
    if entry.get("curve_name") != "derivative" or domain != question.domain:
        raise UnsupportedCondition(
            "the derivative graph and its domain must match the question"
        )
    points = curve_levels.intersections(entry, question.slope)
    result = str(len(points))
    if not question.count:
        marks = [
            (sp.Rational(x), sp.Rational(y))
            for x, y in entry["level_marks"]
            if sp.Rational(y) == question.slope
        ]
        if len(points) != 1 or len(marks) != 1:
            raise UnsupportedCondition(
                "the requested abscissa must be unique and exactly readable"
            )
        x, _ = marks[0]
        if (
            abs(entry["svg_origin"][0] + float(x) * entry["svg_unit"] - points[0][0])
            > entry["svg_unit"] * 0.15
        ):
            raise UnsupportedCondition(
                "the exact grid mark disagrees with the SVG intersection"
            )
        result = answer(x)
    active = {**entry}
    if (
        entry.get("solution_asset")
        and sp.Rational(entry["annotated_level"]) != question.slope
    ):
        active.pop("solution_asset")
    return data, question, active, points, result


def required_assets(context):
    _, _, entry, _, _ = _input(context)
    return graph_input.requirements(entry)


def render_svg(entry, source, question, points):
    root = ET.fromstring(source)
    background = ET.Element("{" + _NS + "}g", {"data-runner-layer": "level"})
    root.insert(entry["svg_level_layer"], background)
    group = ET.SubElement(
        root, "{" + _NS + "}g", {"data-runner-diagram": "derivative_level"}
    )

    def node(tag, *, front=False, **attrs):
        return ET.SubElement(
            group if front else background,
            "{" + _NS + "}" + tag,
            {k.replace("_", "-"): str(v) for k, v in attrs.items()},
        )

    ox, oy = entry["svg_origin"]
    unit = entry["svg_unit"]
    y = oy - float(question.slope) * unit
    x0, y0, width, height = map(float, root.attrib["viewBox"].split())
    if not y0 + 2 < y < y0 + height - 2:
        raise UnsupportedCondition("the requested level is outside the visible graph")
    if entry["diagram_style"] == "green_level":
        node(
            "line",
            x1=x0 + 1,
            y1=y,
            x2=x0 + width - 1,
            y2=y,
            stroke="#0A990A",
            stroke_width=1.25,
        )
        label = node(
            "text",
            front=True,
            x=x0 + width * 0.54,
            y=y + 16,
            fill="#0A990A",
            font_family="Times New Roman, serif",
            font_size=14,
            font_style="italic",
        )
        label.text = "y = " + answer(question.slope)
    elif question.count:
        node(
            "line",
            x1=x0 + 1,
            y1=y,
            x2=x0 + width - 1,
            y2=y,
            stroke="black",
            stroke_width=0.75,
            stroke_dasharray="7.5,3",
        )
        node("rect", front=True, x=ox - 24, y=y - 8, width=23, height=15, fill="white")
        label = node(
            "text",
            front=True,
            x=ox - 12,
            y=y + 5,
            fill="black",
            font_family="Times New Roman, serif",
            font_size=14,
        )
        label.text = answer(question.slope)
    else:
        x = points[0][0]
        node(
            "polyline",
            points=f"{ox},{y} {x},{y} {x},{oy}",
            fill="none",
            stroke="black",
            stroke_width=0.75,
            stroke_dasharray="7.5,3",
        )
    for x, y in points:
        node("circle", front=True, cx=x, cy=y, r=2.3, fill="#143B8F")
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    data, question, entry, points, _ = _input(context)
    if entry.get("solution_asset") or entry["diagram_style"] == "none":
        return ()
    return (
        solution_diagrams.spec(
            entry["diagram_key"], render_svg(entry, data[6], question, points)
        ),
    )


def proof(question, result):
    html = (
        "<p>Значение производной в точке касания равно угловому коэффициенту касательной:</p>"
        + line("f'(x_0)=k")
    )
    if question.comparison is None:
        html += (
            "<p>Касательная параллельна оси абсцисс или совпадает с ней, поэтому её угловой коэффициент равен нулю.</p>"
            + line("k=0")
        )
    else:
        html += (
            "<p>У параллельных или совпадающих прямых угловые коэффициенты равны. Найдём коэффициент при x у данной прямой:</p>"
            + line("y=" + sp.latex(question.comparison))
            + line("k=" + sp.latex(question.slope))
        )
    html += line("f'(x_0)=" + sp.latex(question.slope))
    html += (
        "<p>На рисунке изображён график производной. Поэтому ищем точки его пересечения или касания с горизонтальной прямой:</p>"
        + line("y=" + sp.latex(question.slope))
    )
    if question.count:
        html += (
            "<p>Считаем все такие точки на заданном интервале. Получаем:</p>"
            + line("N=" + result)
        )
    else:
        html += "<p>Такая точка одна. По сетке находим её абсциссу:</p>" + line(
            "x_0=" + result.replace(",", "{,}")
        )
    return html


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question, entry, points, result = _input(context)
    content, condition, ans, solution, _, original, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    obsolete = (
        original.get("solution_asset") if not entry.get("solution_asset") else None
    )
    removed = []
    if obsolete:
        removed = [
            {
                "transformation_target_id": "asset:" + a["asset_key"],
                "operation": "remove",
            }
            for a in content["assets"]
            if a["asset_id"] == obsolete["source_id"]
        ]
        content = {
            **content,
            "assets": [
                a for a in content["assets"] if a["asset_id"] != obsolete["source_id"]
            ],
        }
    svg = (
        render_svg(entry, source, question, points)
        if not entry.get("solution_asset") and entry["diagram_style"] != "none"
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated_solution_assets
    )
    return solution_diagrams.repair(
        condition,
        ans,
        solution,
        result,
        figure + proof(question, result),
        (key,) if key else (),
        tuple(removed) + tuple(changes),
    )
