"""Read a marked point of k√x and retain the parent's coefficient method."""

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import answer
from ..core.errors import ContentPlanError
from ..probability.common import finish, line
from ..triangles.isosceles.planner import _normalized_content, _section
from ..word_problems.math_common import number as decimal
from ..word_problems.motion_chase_proof import section
from .graph_questions import read
from .hyperbola import number
from .linear_svg import NS, frame, snap
from .parabola_svg import curves, point_distance

ASSET_DIR = Path(__file__).parent / "assets/roots"


def parse(context):
    forms, text = read(context)
    if len(forms) != 2 or forms[0] != r"f(x)=k\sqrt{x}":
        raise ContentPlanError("the complete k sqrt(x) graph question is required")
    prefix = r"На рисунке изображен график функции @0@\s*\.\s*Найдите "
    if re.fullmatch(prefix + r"@1@\s*\.", text):
        match = re.fullmatch(r"f\((.+)\)", forms[1])
        mode = "value"
    elif re.fullmatch(prefix + r"значение x\s*,\s*при котором @1@\s*\.", text):
        match = re.fullmatch(r"f\(x\)=(.+)", forms[1])
        mode = "argument"
    else:
        match = None
    if not match:
        raise ContentPlanError("the entire square-root graph question must match")
    target = sp.Rational(number(match[1]))
    if mode == "value" and target < 0:
        raise ContentPlanError("the square-root function requires x >= 0")
    return mode, target


def marked_point(data, mime):
    if not data or str(mime).split(";")[0].lower() != "image/svg+xml":
        raise ContentPlanError("an inspected square-root SVG is required")
    evidence = json.loads((ASSET_DIR / "source-evidence.json").read_text())
    entry = evidence.get(hashlib.sha256(data).hexdigest())
    if not entry or entry["grid_unit"] != [1, 1]:
        raise ContentPlanError(
            "the root graph bytes and coordinate units need inspection"
        )
    root = ET.fromstring(data)
    axes = frame(root)
    xmap, ymap, sx, sy = axes
    actual = curves(root)
    markers = list(root.iter(NS + "circle"))
    if (
        set(actual) != {"#143B8F"}
        or len(markers) != 2
        or any(m.get("fill", "").upper() != "#143B8F" for m in markers)
    ):
        raise ContentPlanError("one blue root curve and two marked points are required")
    points = [
        (snap(float(m.get("cx")), xmap, sx), snap(float(m.get("cy")), ymap, sy))
        for m in markers
    ]
    if (0, 0) not in points or len(set(points)) != 2:
        raise ContentPlanError(
            "the root graph must mark its origin and one other point"
        )
    point = next(p for p in points if p != (0, 0))
    if (
        point[0] <= 0
        or point[1] == 0
        or any(point_distance(p, actual["#143B8F"], axes) > 0.2 for p in points)
    ):
        raise ContentPlanError(
            "the nonzero marked lattice point must lie on the root curve"
        )
    return tuple(map(sp.Integer, point))


def n(value):
    return decimal(value) if value.is_Rational else sp.latex(value)


def coefficient_proof(point, k, *, name="k"):
    x, y = point
    html = f"<p>По графику найдём значение функции в отмеченной точке и подставим его в формулу, чтобы определить коэффициент {name}:</p>"
    html += line("f(" + n(x) + ")=" + n(y))
    html += line(name + r"\cdot\sqrt{" + n(x) + "}=" + n(y))
    if sp.sqrt(x).is_Integer:
        html += line(n(sp.sqrt(x)) + name + "=" + n(y))
    html += line(name + "=" + r"\frac{" + n(y) + r"}{\sqrt{" + n(x) + "}}=" + n(k))
    return html


def proof(mode, target, point, k, result):
    html = coefficient_proof(point, k)
    if mode == "value":
        html += (
            "<p>Таким образом, вычислим значение функции при указанном аргументе:</p>"
        )
        html += line(
            "f(" + n(target) + ")=(" + n(k) + r")\cdot\sqrt{" + n(target) + "}"
        )
        html += line(r"\sqrt{" + n(target) + "}=" + n(sp.sqrt(target)))
        html += line(
            "f("
            + n(target)
            + ")=("
            + n(k)
            + r")\cdot("
            + n(sp.sqrt(target))
            + ")="
            + n(result)
        )
    else:
        html += "<p>Таким образом, найдём аргумент, при котором функция принимает указанное значение. Учтём область определения и знак квадратного корня:</p>"
        html += line(r"x\geq0,\qquad(" + n(k) + r")\cdot\sqrt{x}=" + n(target))
        if k.is_Rational:
            html += line(r"\sqrt{x}=" + n(sp.simplify(target / k)) + r"\geq0")
            html += line("x=(" + n(sp.simplify(target / k)) + ")^2=" + n(result))
        else:
            html += "<p>Обе части имеют одинаковый знак. Возведём их в квадрат и разделим на квадрат коэффициента:</p>"
            html += line(
                n(sp.simplify(k**2)) + "x=(" + n(target) + ")^2=" + n(target**2)
            )
            html += line(
                "x="
                + r"\frac{"
                + n(target**2)
                + "}{"
                + n(sp.simplify(k**2))
                + "}="
                + n(result)
            )
    return section(html, "Решение")


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    mode, target = parse(context)
    content = _normalized_content(context)
    if len(content["assets"]) != 1 or any(
        s.get("asset_keys")
        or BeautifulSoup(s.get("html", ""), "html.parser").select(
            "img, [data-asset-id], [data-asset-key]"
        )
        for s in content["sections"]
        if s.get("key") != "condition"
    ):
        raise ContentPlanError(
            "the root method uses only the original condition figure"
        )
    point = marked_point(condition_asset_bytes, current_asset_content_type)
    k = sp.simplify(point[1] / sp.sqrt(point[0]))
    if mode == "argument" and target / k < 0:
        raise ContentPlanError("the requested value has no preimage on this root graph")
    result = sp.simplify(k * sp.sqrt(target) if mode == "value" else (target / k) ** 2)
    if result.is_Rational is not True:
        raise ContentPlanError(
            "the requested root value must have an exact rational answer"
        )
    condition, ans, solution = (
        _section(content, key) for key in ("condition", "answer", "solution")
    )
    return finish(
        condition, ans, solution, answer(result), proof(mode, target, point, k, result)
    )
