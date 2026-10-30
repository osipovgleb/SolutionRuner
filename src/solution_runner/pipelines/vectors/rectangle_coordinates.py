"""The diagonal of four explicitly given axis-aligned rectangle vertices."""

import re
from fractions import Fraction
from itertools import product

from solution_runner.pipelines.core.numbers import format_answer, format_latex_fraction
from solution_runner.pipelines.probability.common import (
    UnsupportedCondition,
    finish,
    line,
)

from .coordinates import exact_root
from .endpoints import _PAIR, pair
from .geometric import _EVIDENCE, _read

_PATTERN = re.compile(
    r"Найдите длину диагонали прямоугольника, вершины которого имеют координаты (?P<points>.+)\."
)


def dimensions(points):
    xs, ys = sorted({p[0] for p in points}), sorted({p[1] for p in points})
    if (
        len(points) != 4
        or len(xs) != 2
        or len(ys) != 2
        or set(points) != set(product(xs, ys))
    ):
        raise UnsupportedCondition(
            "four distinct axis-aligned rectangle corners are required"
        )
    return xs, ys


def build_context_repair_plan(context):
    content, condition, answer, solution, text = _read(context)
    match = _PATTERN.fullmatch(text)
    if match is None:
        raise UnsupportedCondition(
            "unsupported complete rectangle-coordinate condition"
        )
    tokens = re.findall(_PAIR, match["points"])
    if len(tokens) != 4 or ", ".join(tokens) != match["points"]:
        raise UnsupportedCondition("exactly four coordinate pairs are required")
    points = tuple(pair(t) for t in tokens)
    xs, ys = dimensions(points)
    for asset in content.get("assets", []):
        entry = _EVIDENCE[asset["asset_id"]]
        if entry["shape"] != "coordinate_rectangle" or {
            tuple(map(Fraction, p)) for p in entry["vertices"]
        } != set(points):
            raise UnsupportedCondition(
                "the coordinate rectangle diagram is incompatible with the vertices"
            )
    width, height = xs[1] - xs[0], ys[1] - ys[0]
    square = width * width + height * height
    result = exact_root(square)
    f = format_latex_fraction
    html = "<p>Найдём длину и ширину прямоугольника как разности соответствующих координат его вершин:</p>"
    html += line(rf"a=({f(xs[1])})-({f(xs[0])})={f(width)}")
    html += line(rf"b=({f(ys[1])})-({f(ys[0])})={f(height)}")
    html += (
        "<p>Диагональ — гипотенуза прямоугольного треугольника. По теореме Пифагора:</p>"
        + line(r"d^2=a^2+b^2")
    )
    html += line(rf"d^2=({f(width)})^2+({f(height)})^2={f(square)}")
    html += line(rf"d=\sqrt{{{f(square)}}}={f(result)}")
    return finish(condition, answer, solution, format_answer(result), html)
