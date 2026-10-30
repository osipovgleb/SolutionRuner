"""Graph areas and primitive differences with exact, checksum-bound models."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.numbers import parse_rational
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition
from . import curve_levels, graph_input, graph_integral_proof, graph_piecewise_primitive
from .common import X, answer, polynomial

_NUMBER = r"-?\d+(?:[,.]\d+)?"
_PREFIX = r"На рисунке изображен график (?:некоторой )?функции y=f\(x\)"
_DIFFERENCE = re.compile(
    _PREFIX
    + rf"\(два луча с общей начальной точкой\)\. Пользуясь рисунком, вычислите F\((?P<upper>{_NUMBER})\)-\s*F\((?P<lower>{_NUMBER})\), где F\(x\)— одна из первообразных функции f\(x\)\."
)
_INTEGRAL = re.compile(
    _PREFIX
    + rf"\. Пользуясь рисунком, вычислите определенный интеграл \\int_\{{(?P<lower>{_NUMBER})\}}\^\{{(?P<upper>{_NUMBER})\}} f\(x\)\\,dx\."
)
_AREA = re.compile(
    _PREFIX
    + r"\. Функция F\(x\)=(?P<primitive>.+?)\s*— одна из первообразных функции (?:y=)?f\(x\)\. Найдите площадь закрашенной фигуры\."
)


@dataclass(frozen=True)
class Question:
    operation: str
    lower: sp.Rational | None = None
    upper: sp.Rational | None = None
    primitive: sp.Expr | None = None


@dataclass(frozen=True)
class PiecewiseIntegral:
    lower: sp.Rational
    upper: sp.Rational
    height: sp.Rational
    join: sp.Rational
    zero: sp.Rational
    slope: sp.Rational
    right: sp.Expr
    right_primitive: sp.Expr
    adjustment: sp.Rational
    result: sp.Rational


@dataclass(frozen=True)
class QuadraticArea:
    lower: sp.Rational
    upper: sp.Rational
    primitive: sp.Expr
    function: sp.Expr
    center: sp.Rational
    curvature: sp.Rational
    vertex_height: sp.Rational
    result: sp.Rational


def rational(text):
    value = parse_rational(text)
    return sp.Rational(value.numerator, value.denominator)


def parse(text):
    text = text.replace("−", "-").replace("–", "-")
    difference = _DIFFERENCE.fullmatch(text)
    integral = _INTEGRAL.fullmatch(text)
    match = difference or integral
    if match:
        return Question(
            "difference" if difference else "integral",
            rational(match["lower"]),
            rational(match["upper"]),
        )
    area = _AREA.fullmatch(text)
    if area:
        return Question("area", primitive=polynomial(area["primitive"], X))
    raise UnsupportedCondition(
        "a complete graph integral or primitive question is required"
    )


def verify_rays(entry):
    h, c, z = (
        sp.Rational(entry[key]) for key in ["plateau_height", "join_x", "zero_x"]
    )
    if h <= 0 or c >= z:
        raise UnsupportedCondition(
            "a positive plateau and a descending ray are required"
        )
    flat, falling = entry["ray_lines"]
    (_fx, fy), (cx, cy) = flat
    (rx, ry), (ex, ey) = falling
    ox, oy = entry["svg_origin"]
    ux, uy = entry["svg_units"]
    if (
        ux <= 0
        or uy <= 0
        or abs(fy - cy) > 0.1
        or abs(cx - rx) > 1
        or abs(cy - ry) > 1
        or ex <= rx
        or ey <= ry
    ):
        raise UnsupportedCondition("the reviewed rays must meet at one corner")
    native_zero = rx + (oy - ry) * (ex - rx) / (ey - ry)
    if any(
        abs(float(actual) - expected) > 0.1 * unit
        for actual, expected, unit in [
            (c * ux + ox, cx, ux),
            (oy - h * uy, cy, uy),
            (ox + z * ux, native_zero, ux),
        ]
    ):
        raise UnsupportedCondition(
            "the ray coordinates disagree with the labelled grid"
        )
    return h, c, z


def piecewise_model(question, entry):
    h, c, z = verify_rays(entry)
    a, b = question.lower, question.upper
    if a is None or b is None or not a < c < b or b != z:
        raise UnsupportedCondition(
            "the reviewed shaded trapezoid must cross the corner above the axis"
        )
    if [a, b] != list(map(sp.Rational, entry["illustration_span"])):
        raise UnsupportedCondition(
            "the source shading does not match the integration bounds"
        )
    slope = -h / (z - c)
    right = sp.expand(h + slope * (X - c))
    primitive = sp.integrate(right, X)
    adjustment = sp.simplify(h * c - primitive.subs(X, c))
    result = sp.simplify(primitive.subs(X, b) + adjustment - h * a)
    geometric = h * (c - a) + (b - c) * (h + right.subs(X, b)) / 2
    if sp.simplify(result - geometric) != 0:
        raise UnsupportedCondition("the geometric and analytic areas disagree")
    return PiecewiseIntegral(a, b, h, c, z, slope, right, primitive, adjustment, result)


def verify_parabola(entry):
    left, right = entry["area_svg_span"]
    oy = entry["svg_origin"][1]
    if left >= right:
        raise UnsupportedCondition("the shaded graph interval must be ordered")
    samples = [
        curve_levels.at_abscissa(entry, left + (right - left) * t)
        for t in [0.25, 0.5, 0.75]
    ]
    bowl = entry["area_kind"] == "bowl"
    if any(y >= oy for group in samples for y, _ in group):
        raise UnsupportedCondition("the shaded graph must lie above the axis")
    if any(slope * (1 if bowl else -1) >= -0.01 for _, slope in samples[0]) or any(
        slope * (1 if bowl else -1) <= 0.01 for _, slope in samples[2]
    ):
        raise UnsupportedCondition("the reviewed parabola has changed its orientation")


def area_model(question, entry):
    primitive = question.primitive
    f = sp.diff(primitive, X)
    p = sp.Poly(f, X)
    if p.degree() != 2 or tuple(p.all_coeffs()) != tuple(
        map(sp.Rational, entry["derivative_coefficients"])
    ):
        raise UnsupportedCondition(
            "the stated primitive derivative does not match the reviewed graph"
        )
    a, b = map(sp.Rational, entry["area_span"])
    curvature = p.nth(2)
    center = -p.nth(1) / (2 * curvature)
    height = sp.simplify(f.subs(X, center))
    if a >= b or center != (a + b) / 2 or height <= 0:
        raise UnsupportedCondition(
            "the shaded interval must be symmetric about the positive vertex"
        )
    if entry["area_kind"] == "bowl":
        if curvature <= 0:
            raise UnsupportedCondition("the shaded positive bowl must open upward")
    elif (
        entry["area_kind"] != "cap"
        or curvature >= 0
        or f.subs(X, a) != 0
        or f.subs(X, b) != 0
    ):
        raise UnsupportedCondition("the shaded cap must end at both roots")
    verify_parabola(entry)
    result = sp.simplify(primitive.subs(X, b) - primitive.subs(X, a))
    if result <= 0:
        raise UnsupportedCondition("the shaded area must be positive")
    return QuadraticArea(a, b, primitive, f, center, curvature, height, result)


def calculate(context):
    data = graph_input.read_graph(context)
    entry = data[5]
    question = parse(data[4])
    if entry.get("curve_name") != "f":
        raise UnsupportedCondition("the diagram must show the integrand function")
    if question.operation == "area" and entry.get("integral_model") == "quadratic":
        model = area_model(question, entry)
    elif (
        question.operation in ["difference", "integral"]
        and entry.get("integral_model") == "rays"
    ):
        model = piecewise_model(question, entry)
    else:
        raise UnsupportedCondition("the mathematical graph model and request disagree")
    return data, question, model


def required_assets(context):
    data, _, _ = calculate(context)
    return graph_input.requirements(data[5])


def build_context_repair_plan(context, *, condition_asset_bytes=None):
    data, question, model = calculate(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    obsolete = set(entry.get("bibliography_assets", []))
    removed = tuple(
        {"transformation_target_id": "asset:" + a["asset_key"], "operation": "remove"}
        for a in content["assets"]
        if a["asset_id"] in obsolete
    )
    filtered = {
        **content,
        "assets": [a for a in content["assets"] if a["asset_id"] not in obsolete],
    }
    figure, key, changes = graph_input.figure(filtered, entry)
    html = (
        graph_integral_proof.area(model, entry)
        if question.operation == "area"
        else graph_piecewise_primitive.piecewise(model, question.operation)
    )
    return solution_diagrams.repair(
        condition,
        ans,
        solution,
        answer(model.result),
        figure + html,
        (key,) if key else (),
        removed + tuple(changes),
    )
