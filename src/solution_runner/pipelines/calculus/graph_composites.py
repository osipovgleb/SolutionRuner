"""Differentiate a typed composition, or evaluate it, using the same graph evidence."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import sympy as sp

from ..equations.power_arithmetic import clean
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import graph_input
from .common import X, answer, polynomial

U, V = sp.symbols("u v", real=True)
_NS = "http://www.w3.org/2000/svg"
_ORIGIN = re.compile(
    r"На рисунке изображен график функции y=f\(x\)\. Прямая, проходящая через начало координат, "
    r"касается графика этой функции в точке с абсциссой (?P<x>\d+)\. Найдите f'\((?P<at>\d+)\)\."
)
_COMPOSITE = re.compile(
    r"На рисунке изображены график функции y=f\(x\)\s*и касательная к этому графику, "
    r"проведенная в точке x_0(?:=(?P<at>[−–-]?\d+))?\. "
    r"(?P<label>Уравнение касательной показано на рисунке\. )?"
    r"Найдите значение (?P<derivative>производной )?функции g\(x\)=(?P<expression>.+?)\s*в точке x_0\."
)


@dataclass
class Question:
    origin: bool
    derivative: bool
    expression: sp.Expr | None
    slope: sp.Expr
    point: dict


def composition(text):
    text = clean(text)
    constant = sp.S.Zero
    logarithm = re.search(r"([+-])\\ln(\d+)$", text)
    if logarithm:
        n = int(logarithm[2])
        if not 0 < n <= 10**6:
            raise UnsupportedCondition(
                "a real bounded logarithmic constant is required"
            )
        constant = (1 if logarithm[1] == "+" else -1) * sp.log(n)
        text = text[: logarithm.start()]
    # Source functions are the only declarations of the two placeholder variables.
    if re.search("[uv]", text):
        raise UnsupportedCondition("undeclared composition placeholder")
    text = text.replace("f'(x)", "v").replace("f(x)", "u")
    return polynomial(text, X, ("u", "v")) + constant


def calculate(expression, derivative, entry):
    tangent = graph_input.tangent(entry)
    slope = sp.diff(tangent, X)
    point = graph_input.contact(entry)
    if derivative:
        if V in expression.free_symbols:
            raise UnsupportedCondition(
                "a second derivative is not specified by a tangent"
            )
        evaluated = sp.diff(expression, X) + sp.diff(expression, U) * V
    else:
        evaluated = expression
    substitutions = {V: slope}
    if "x" in point:
        substitutions[X] = point["x"]
    if "y" in point:
        substitutions[U] = point["y"]
    value = sp.simplify(evaluated.subs(substitutions))
    if value.free_symbols:
        raise UnsupportedCondition("the graph does not determine all requested values")
    return evaluated, value


def _input(context):
    data = graph_input.read_graph(context)
    text, entry = data[4:6]
    tangent = graph_input.tangent(entry)
    slope = sp.diff(tangent, X)
    point = graph_input.contact(entry)
    origin = _ORIGIN.fullmatch(text)
    if origin:
        x = sp.Rational(origin["x"])
        if (
            x == 0
            or x != sp.Rational(origin["at"])
            or point.get("x") != x
            or tangent.subs(X, 0) != 0
        ):
            raise UnsupportedCondition(
                "the marked contact and the origin tangent must match the question"
            )
        question = Question(True, True, None, slope, point)
    else:
        match = _COMPOSITE.fullmatch(text)
        if not match:
            raise UnsupportedCondition(
                "unsupported complete graph composition question"
            )
        if bool(match["label"]) != ("equation" in entry):
            raise UnsupportedCondition(
                "the tangent equation must be present exactly when stated"
            )
        if match["at"] is not None and point.get("x") != sp.Rational(
            clean(match["at"])
        ):
            raise UnsupportedCondition(
                "the stated abscissa disagrees with the marked contact"
            )
        question = Question(
            False,
            bool(match["derivative"]),
            composition(match["expression"]),
            slope,
            point,
        )
        calculate(question.expression, question.derivative, entry)
    return data, question


def required_assets(context):
    data, _ = _input(context)
    return graph_input.requirements(data[5])


def render_origin_tangent(entry, source):
    point = graph_input.contact(entry)
    tangent = graph_input.tangent(entry)
    if tangent.subs(X, 0) != 0 or "x" not in point:
        raise UnsupportedCondition("the origin tangent needs a verified contact point")
    root = ET.fromstring(source)
    ox, oy = entry["svg_origin"]
    ux, uy = entry["svg_unit"]
    left, top, right, bottom = entry["svg_bounds"]
    slope = float(sp.diff(tangent, X))
    intersections = []
    for x in [left, right]:
        y = oy - slope * (x - ox) * uy / ux
        if top <= y <= bottom:
            intersections.append((x, y))
    if slope:
        for y in [top, bottom]:
            x = ox + (oy - y) * ux / (slope * uy)
            if left < x < right:
                intersections.append((x, y))
    if len(intersections) != 2:
        raise UnsupportedCondition("the tangent must cross the source grid twice")
    group = ET.SubElement(
        root, "{" + _NS + "}g", {"data-runner-diagram": "origin_tangent"}
    )
    (x1, y1), (x2, y2) = intersections
    ET.SubElement(
        group,
        "{" + _NS + "}line",
        {
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "fill": "none",
            "stroke": "#0A990A",
            "stroke-width": "1.25",
        },
    )
    lx, ly = entry["svg_label"]
    label = ET.SubElement(
        group,
        "{" + _NS + "}text",
        {
            "x": str(lx),
            "y": str(ly),
            "font-family": "Times New Roman, serif",
            "font-size": "16",
            "font-style": "italic",
            "fill": "#0A990A",
        },
    )
    label.text = "y = kx"
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    data, _ = _input(context)
    entry, source = data[5:]
    return (
        (
            solution_diagrams.spec(
                entry.get("diagram_key", graph_input.KEY),
                render_origin_tangent(entry, source),
            ),
        )
        if entry.get("origin_tangent_overlay")
        else ()
    )


def _composition_latex(expression):
    result = sp.latex(expression).replace(r"\log", r"\ln")
    return re.sub(r"\bu\b", "f(x)", re.sub(r"\bv\b", "f'(x)", result))


def proof(question, entry):
    slope, point = question.slope, question.point
    if question.origin:
        x, y = point["x"], point["y"]
        html = (
            "<p>Поскольку касательная проходит через начало координат, её уравнение имеет вид:</p>"
            + line("y=kx")
        )
        html += f"<p>По рисунку точка касания имеет координаты ({answer(x)}; {answer(y)}). Подставим их в уравнение прямой:</p>"
        html += line(rf"{sp.latex(y)}=k\cdot {sp.latex(x)}")
        html += line(rf"k=\frac{{{sp.latex(y)}}}{{{sp.latex(x)}}}={sp.latex(slope)}")
        html += "<p>Угловой коэффициент касательной равен значению производной в точке касания:</p>"
        html += line(rf"f'({sp.latex(x)})=k={answer(slope).replace(',', '{,}')}")
        return answer(slope), html
    expression = question.expression
    evaluated, value = calculate(expression, question.derivative, entry)
    if question.derivative:
        html = "<p>Найдём производную функции g(x), пользуясь правилами дифференцирования:</p>"
        html += line("g(x)=" + _composition_latex(expression))
        html += line("g'(x)=" + _composition_latex(evaluated))
    else:
        html = "<p>Найдём значение производной f в точке касания, чтобы подставить его в заданную функцию:</p>"
        html += line("g(x)=" + _composition_latex(expression))
    html += "<p>Значение производной в точке касания равно угловому коэффициенту касательной.</p>"
    if "equation" in entry:
        html += line("y=" + sp.latex(graph_input.tangent(entry)))
    else:
        p, q = entry["line_points"]
        html += "<p>По отмеченным на сетке точкам находим отношение приращения ординаты к приращению абсциссы:</p>"
        html += line(
            rf"k=\frac{{{sp.latex(sp.Rational(q[1]))}-({sp.latex(sp.Rational(p[1]))})}}{{{sp.latex(sp.Rational(q[0]))}-({sp.latex(sp.Rational(p[0]))})}}={sp.latex(slope)}"
        )
    html += line("f'(x_0)=k=" + sp.latex(slope))
    needed = evaluated.free_symbols
    if X in needed:
        html += line("x_0=" + sp.latex(point["x"]))
    if U in needed:
        html += line("f(x_0)=" + sp.latex(point["y"]))
    # Keep the numerical substitution visible before SymPy reduces it.
    raw = _composition_latex(evaluated).replace("f'(x)", "(" + sp.latex(slope) + ")")
    if U in needed:
        raw = raw.replace("f(x)", "(" + sp.latex(point["y"]) + ")")
    if X in needed:
        raw = re.sub(r"\bx\b", lambda _: "(" + sp.latex(point["x"]) + ")", raw)
    name = "g'(x_0)" if question.derivative else "g(x_0)"
    html += (
        "<p>Подставим найденные значения в выражение для искомой величины:</p>"
        + line(name + "=" + raw)
    )
    exact, decimal = sp.latex(value), answer(value).replace(",", "{,}")
    html += line(name + "=" + exact + ("=" + decimal if exact != decimal else ""))
    return answer(value), html


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question = _input(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(question, entry)
    svg = (
        render_origin_tangent(entry, source)
        if entry.get("origin_tangent_overlay")
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated_solution_assets
    )
    return solution_diagrams.repair(
        condition, ans, solution, result, figure + html, (key,) if key else (), changes
    )
