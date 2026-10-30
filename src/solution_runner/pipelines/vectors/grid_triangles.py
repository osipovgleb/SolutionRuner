"""A grid triangle keeps both the geometric proof and the coordinate method."""

import hashlib
import re
import xml.etree.ElementTree as ET
from fractions import Fraction

import sympy as sp

from solution_runner.pipelines.probability import condition_diagram, solution_diagrams
from solution_runner.pipelines.probability.common import UnsupportedCondition, line

from .coordinate_diagrams import _ASSETS, _EVIDENCE
from .coordinates import _fmt, solve
from .geometric import _triangle

_KEY = "triangle_coordinates"
_ALT = "Треугольник ABC в системе координат"
_PATTERN = re.compile(
    r"На клетчатой бумаге с размером клетки 1\\times\s*1 изображен треугольник ABC\. Найдите скалярное произведение \\overrightarrow\{AB\}\\cdot\s*\\overrightarrow\{AC\}\."
)
_NS = "http://www.w3.org/2000/svg"


def _input(context):
    content, condition, answer, solution, text, entry, source = condition_diagram.read(
        context, _EVIDENCE, _ASSETS, identifiers=("ABC",)
    )
    if not _PATTERN.fullmatch(text) or set(entry.get("vertices", {})) != {
        "A",
        "B",
        "C",
    }:
        raise UnsupportedCondition(
            "the audited triangle and complete grid question are required"
        )
    vectors = {
        name: tuple(Fraction(y) - Fraction(x) for x, y in zip(start, end, strict=True))
        for name, (start, end) in entry["vectors"].items()
    }
    return content, condition, answer, solution, entry, source, vectors


def render_svg(entry, source):
    root = ET.fromstring(source)
    ox, oy = entry["svg_origin"]
    unit = entry["svg_unit"]
    width, height = map(float, root.attrib["viewBox"].split()[2:])

    def node(tag, **attrs):
        return ET.SubElement(
            root,
            "{" + _NS + "}" + tag,
            {k.replace("_", "-"): str(v) for k, v in attrs.items()},
        )

    node(
        "line",
        x1=ox,
        y1=height - 0.71,
        x2=ox,
        y2=4.982,
        stroke="black",
        stroke_width=0.75,
    )
    node("polygon", points=f"{ox},10.006 {ox - 4.5},16.011 {ox},1 {ox + 4.5},16.011")
    node(
        "line",
        x1=1.024,
        y1=oy,
        x2=width - 6.839,
        y2=oy,
        stroke="black",
        stroke_width=0.75,
    )
    node(
        "polygon",
        points=f"{width - 10.005},{oy} {width - 16.011},{oy - 4.5} {width - 1},{oy} {width - 16.011},{oy + 4.5}",
    )
    for text, x, y, italic in [
        ("O", ox - 14, oy + 14, True),
        ("x", width - 12, oy + 13, True),
        ("y", ox - 14, 14, True),
        ("1", ox + unit - 3, oy + 15, False),
        ("1", ox - 13, oy - unit - 3, False),
    ]:
        label = node(
            "text",
            x=x,
            y=y,
            font_family="Times New Roman, serif",
            font_size=14,
            font_style="italic" if italic else "normal",
        )
        label.text = text
    return ET.tostring(root, encoding="unicode")


def required_assets(context):
    *_, entry, _source, _vectors = _input(context)
    asset = entry.get("coordinate_asset")
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


def diagram_specs(context):
    *_, entry, source, _vectors = _input(context)
    return (
        ()
        if entry.get("coordinate_asset")
        else (solution_diagrams.spec(_KEY, render_svg(entry, source)),)
    )


def _figure(content, entry, source, generated):
    asset = entry.get("coordinate_asset")
    if asset:
        svg = (_ASSETS / (asset["source_id"] + ".svg")).read_bytes()
        if hashlib.sha256(svg).hexdigest() != asset["sha256"]:
            raise UnsupportedCondition("the audited coordinate figure has changed")
    allowed = {
        a["asset_id"]
        for a in content.get("assets", [])
        if a.get("asset_key")
        in next(s for s in content["sections"] if s["key"] == "condition")["asset_keys"]
    }
    allowed.update(
        [asset["source_id"]]
        if asset
        else [
            a["source_asset_id"]
            for a in generated
            if a.get("asset_key") == _KEY
            and a.get("sha256")
            == solution_diagrams.spec(_KEY, render_svg(entry, source))["sha256"]
        ]
    )
    if any(a["asset_id"] not in allowed for a in content.get("assets", [])):
        raise UnsupportedCondition("foreign triangle solution assets are unsupported")
    return solution_diagrams.image(
        content,
        _KEY,
        _ALT,
        source_id=asset["source_id"] if asset else None,
        svg=None if asset else render_svg(entry, source),
        generated=generated,
    )


def geometric_proof(vectors):
    ab, ac = vectors["AB"], vectors["AC"]
    bc = tuple(y - x for x, y in zip(ab, ac, strict=True))
    squares = [sum(x * x for x in vector) for vector in (ac, bc, ab)]
    ac2, bc2, ab2 = squares
    if not ac2 or not bc2 or ab2 != ac2 + bc2:
        raise UnsupportedCondition(
            "the source geometric method needs a nondegenerate right angle at C"
        )
    f = lambda x: sp.latex(sp.Rational(x.numerator, x.denominator))
    html = "<p>Первый способ. Найдём стороны треугольника по теореме Пифагора. Катеты вспомогательных прямоугольных треугольников считаем по клеткам:</p>"
    for name, vector, square in zip(
        ("AC", "BC", "AB"), (ac, bc, ab), squares, strict=True
    ):
        html += line(
            rf"{name}^2=("
            + _fmt(abs(vector[0]))
            + r")^2+("
            + _fmt(abs(vector[1]))
            + r")^2="
            + f(square)
        )
        html += line(
            rf"{name}=\sqrt{{{f(square)}}}="
            + sp.latex(sp.sqrt(sp.Rational(square.numerator, square.denominator)))
        )
    html += (
        "<p>Квадрат большей стороны равен сумме квадратов меньших сторон. По обратной теореме Пифагора угол C прямой:</p>"
        + line(rf"AB^2={f(ab2)}={f(ac2)}+{f(bc2)}=AC^2+BC^2")
    )
    value, proof, _ = _triangle(
        {},
        "right",
        sp.sqrt(sp.Rational(ac2.numerator, ac2.denominator)),
        "dot",
        "AB*AC",
    )
    return value, html + proof


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    content, condition, answer, solution, entry, source, vectors = _input(context)
    condition_diagram.verify_download(source, condition_asset_bytes)
    value, html = geometric_proof(vectors)
    figure, key, changes = _figure(content, entry, source, generated_solution_assets)
    html += (
        "<p>Второй способ. Введём систему координат, как показано на рисунке:</p>"
        + figure
    )
    for name, vector in vectors.items():
        html += line(rf"\overrightarrow{{{name}}}=" + _fmt(vector))
    result, steps = solve(
        vectors, "scalar", r"\overrightarrow{AB}\cdot\overrightarrow{AC}"
    )
    if sp.Rational(result.replace(",", ".")) != value:
        raise UnsupportedCondition(
            "the independent geometric and coordinate calculations disagree"
        )
    return solution_diagrams.repair(
        condition, answer, solution, result, html + steps, (key,), changes
    )
