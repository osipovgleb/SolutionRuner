"""Read audited graph coordinates and keep the source triangle proof and figure."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

from bs4 import BeautifulSoup

from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from .common import answer, read

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "tangent_evidence.json").read_text())
_KEY = "tangent_triangle"
_ALT = "Касательная и прямоугольный треугольник для вычисления её наклона"
_NS = "http://www.w3.org/2000/svg"
_QUESTION = re.compile(
    r"На рисунке (?:изображен|изображены) график функции y=f\(x\)\s*и касательная к нему "
    r"в точке с абсциссой x_0\. Найдите значение производной функции f\(x\)\s*в точке x_0\."
)


def _read_text(context):
    prepared = deepcopy(context)
    condition = next(
        s for s in prepared["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    for tag in soup.find_all("sub"):
        if tag.parent.name == "sub":
            continue
        if (
            tag.attrs
            or tag.get_text() != "0"
            or any(
                child.name != "sub" or child.attrs or child.find(True)
                for child in tag.find_all(True)
            )
        ):
            raise UnsupportedCondition("only the source x-zero subscript is supported")
        tag.replace_with("_0")
    condition["html"] = str(soup)
    cond, ans, solution, text = read(prepared)
    text = re.sub(r"\s*([=()])\s*", r"\1", text)
    text = re.sub(r"x\s*_\{?0\}?", "x_0", text)
    return prepared["normalized_content"], cond, ans, solution, text


def model(entry):
    vertices = {
        name: tuple(map(Fraction, xy)) for name, xy in entry["vertices"].items()
    }
    if set(vertices) != {"A", "B", "C"}:
        raise UnsupportedCondition("the source triangle needs three named vertices")
    right = [
        name
        for name, p in vertices.items()
        if {q[0] == p[0] for n, q in vertices.items() if n != name} == {True, False}
        and {q[1] == p[1] for n, q in vertices.items() if n != name} == {True, False}
    ]
    if len(right) != 1:
        raise UnsupportedCondition(
            "a nondegenerate axis-aligned right triangle is required"
        )
    r = right[0]
    v = next(n for n, p in vertices.items() if n != r and p[0] == vertices[r][0])
    h = next(n for n, p in vertices.items() if n != r and p[1] == vertices[r][1])
    rise = vertices[v][1] - vertices[h][1]
    run = vertices[v][0] - vertices[h][0]
    p, q = (tuple(map(Fraction, xy)) for xy in entry["line_points"])
    if p[0] == q[0] or (q[1] - p[1]) / (q[0] - p[0]) != rise / run:
        raise UnsupportedCondition("the triangle and the source tangent disagree")
    for endpoint in (vertices[v], vertices[h]):
        if (endpoint[1] - p[1]) * (q[0] - p[0]) != (endpoint[0] - p[0]) * (q[1] - p[1]):
            raise UnsupportedCondition(
                "the triangle hypotenuse must lie on the tangent"
            )
    return vertices, r, v, h, rise / run


def _input(context):
    result = condition_diagram.read(
        context, _EVIDENCE, _ASSETS, content_reader=_read_text
    )
    if not _QUESTION.fullmatch(result[4]):
        raise UnsupportedCondition(
            "the complete graph-tangent derivative question is required"
        )
    model(result[5])
    return result


def required_assets(context):
    *_, entry, _ = _input(context)
    asset = entry.get("solution_asset")
    return (
        (
            {
                "source_asset_id": asset["source_id"],
                "section_id": "solution:1",
                "alt_text": _ALT,
            },
        )
        if asset
        else ()
    )


def render_svg(entry, source):
    vertices, r, v, h, _ = model(entry)
    root = ET.fromstring(source)
    ox, oy = entry["svg_origin"]
    ux, uy = entry["svg_unit"]
    points = {
        name: (ox + float(x) * ux, oy - float(y) * uy)
        for name, (x, y) in vertices.items()
    }
    group = ET.SubElement(root, "{" + _NS + "}g", {"data-runner-diagram": _KEY})

    def node(tag, **attrs):
        return ET.SubElement(
            group,
            "{" + _NS + "}" + tag,
            {k.replace("_", "-"): str(v) for k, v in attrs.items()},
        )

    path = " ".join(
        f"{x:.3f},{y:.3f}" for x, y in (points[h], points[r], points[v], points[h])
    )
    node(
        "polyline",
        points=path,
        fill="none",
        stroke="#007EA5",
        stroke_width=1.25,
        stroke_linecap="round",
        stroke_linejoin="round",
    )
    rx, ry = points[r]
    dx = 12 if points[h][0] > rx else -12
    dy = 12 if points[v][1] > ry else -12
    node(
        "polyline",
        points=f"{rx + dx},{ry} {rx + dx},{ry + dy} {rx},{ry + dy}",
        fill="none",
        stroke="#007EA5",
        stroke_width=1.25,
    )
    for name, (x, y) in points.items():
        node("circle", cx=x, cy=y, r=2.1, fill="#007EA5")
        label = node(
            "text",
            x=x - 14 if name == h else x + 5,
            y=y - 5 if name == v else y + 16,
            fill="black",
            font_family="Times New Roman, serif",
            font_size=16,
            font_style="italic",
        )
        label.text = name
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    *_, entry, source = _input(context)
    return (
        ()
        if entry.get("solution_asset")
        else (solution_diagrams.spec(_KEY, render_svg(entry, source)),)
    )


def _figure(content, entry, source, generated):
    asset = entry.get("solution_asset")
    svg = None if asset else render_svg(entry, source)
    if (
        asset
        and hashlib.sha256(
            (_ASSETS / (asset["source_id"] + ".svg")).read_bytes()
        ).hexdigest()
        != asset["sha256"]
    ):
        raise UnsupportedCondition("the audited solution triangle has changed")
    allowed = {
        a["asset_id"]
        for a in content["assets"]
        if a["asset_key"]
        in next(s for s in content["sections"] if s["key"] == "condition")["asset_keys"]
    }
    allowed.update(
        [asset["source_id"]]
        if asset
        else [
            a["source_asset_id"]
            for a in generated
            if a.get("asset_key") == _KEY
            and a.get("sha256") == solution_diagrams.spec(_KEY, svg)["sha256"]
        ]
    )
    if any(a["asset_id"] not in allowed for a in content["assets"]):
        raise UnsupportedCondition("an unrelated graph solution asset is present")
    return solution_diagrams.image(
        content,
        _KEY,
        _ALT,
        source_id=asset["source_id"] if asset else None,
        svg=svg,
        generated=generated,
    )


def proof(entry):
    vertices, r, v, h, slope = model(entry)
    vertical, horizontal = "".join(sorted(v + r)), "".join(sorted(h + r))
    height = abs(vertices[v][1] - vertices[r][1])
    width = abs(vertices[h][0] - vertices[r][0])
    angle = v + h + r
    html = "<p>Значение производной в точке касания равно угловому коэффициенту касательной, который, в свою очередь, равен тангенсу угла наклона данной касательной к оси абсцисс.</p>"
    html += line(r"f'(x_0)=k=\operatorname{tg}\alpha")
    html += "<p>Построим прямоугольный треугольник с вершинами в точках "
    html += (
        ", ".join(
            f"{name} ({answer(x)}; {answer(y)})" for name, (x, y) in vertices.items()
        )
        + f". Длины катетов находим по клеткам; прямой угол — при вершине {r}.</p>"
    )
    html += line(
        rf"{vertical}=\left|{answer(vertices[v][1])}-({answer(vertices[r][1])})\right|={answer(height)}"
    )
    html += line(
        rf"{horizontal}=\left|{answer(vertices[h][0])}-({answer(vertices[r][0])})\right|={answer(width)}"
    )
    html += line(
        rf"\operatorname{{tg}}\angle {angle}=\frac{{{vertical}}}{{{horizontal}}}=\frac{{{answer(height)}}}{{{answer(width)}}}"
    )
    if slope > 0:
        html += f"<p>Угол наклона касательной к оси абсцисс равен углу {angle}. Поэтому:</p>"
        expression = rf"\operatorname{{tg}}\angle {angle}"
    else:
        html += f"<p>Касательная убывает. Её угол наклона к оси абсцисс смежный с углом {angle}, поэтому тангенс отрицателен:</p>"
        expression = rf"\operatorname{{tg}}(180^\circ-\angle {angle})=-\operatorname{{tg}}\angle {angle}"
    html += line(
        rf"f'(x_0)={expression}="
        + ("-" if slope < 0 else "")
        + rf"\frac{{{answer(height)}}}{{{answer(width)}}}={answer(slope)}"
    )
    return answer(slope), html


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    content, condition, ans, solution, _, entry, source = _input(context)
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(entry)
    figure, key, changes = _figure(content, entry, source, generated_solution_assets)
    return solution_diagrams.repair(
        condition, ans, solution, result, figure + html, (key,), changes
    )
