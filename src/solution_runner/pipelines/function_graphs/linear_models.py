"""One exact affine model for value, inverse and intersection graph questions."""

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from bs4 import BeautifulSoup

from ..calculus.common import answer
from ..core.errors import ContentPlanError
from ..probability.common import finish
from ..triangles.isosceles.planner import _normalized_content, _section
from . import linear_questions, linear_svg

ASSET_DIR = Path(__file__).parent / "assets/linear"


def registry():
    return json.loads((ASSET_DIR / "source-evidence.json").read_text())


@dataclass(frozen=True)
class Line:
    color: str
    points: tuple

    @property
    def slope(self):
        p, q = self.points
        if p[0] == q[0]:
            raise ContentPlanError("a linear-function graph cannot be vertical")
        return (q[1] - p[1]) / (q[0] - p[0])

    @property
    def intercept(self):
        x, y = self.points[0]
        return y - self.slope * x

    def value(self, x):
        return self.slope * x + self.intercept


@dataclass(frozen=True)
class Analysis:
    kind: str
    target: Fraction | None
    lines: tuple[Line, ...]
    intersection: tuple | None
    result: Fraction


def analyze(kind, target, lines):
    if kind in {"value", "argument"}:
        if len(lines) != 1:
            raise ContentPlanError(
                "one linear graph is required for a function value or argument"
            )
        one = lines[0]
        if kind == "argument" and one.slope == 0:
            raise ContentPlanError("a constant function has no unique inverse argument")
        result = (
            one.value(target)
            if kind == "value"
            else (target - one.intercept) / one.slope
        )
        return Analysis(kind, target, lines, None, result)
    if len(lines) != 2 or lines[0].slope == lines[1].slope:
        raise ContentPlanError(
            "two nonparallel lines are required for a unique intersection"
        )
    first, second = lines
    x = (second.intercept - first.intercept) / (first.slope - second.slope)
    y = first.value(x)
    return Analysis(kind, None, lines, (x, y), x if kind == "intersection_x" else y)


def calculate(context, data, mime):
    content = _normalized_content(context)
    kind, target = linear_questions.parse(context)
    for section in content["sections"]:
        if section.get("key") != "condition" and (
            section.get("asset_keys")
            or BeautifulSoup(section.get("html", ""), "html.parser").select(
                "img, [data-asset-id], [data-asset-key]"
            )
        ):
            raise ContentPlanError(
                "these linear graph methods use only the original condition image"
            )
    if (
        len(content["assets"]) != 1
        or str(mime).split(";")[0].lower() != "image/svg+xml"
        or not data
    ):
        raise ContentPlanError("one inspected SVG condition image is required")
    entry = registry().get(hashlib.sha256(data).hexdigest())
    if not entry or entry["grid_unit"] != [1, 1]:
        raise ContentPlanError(
            "the graph bytes and coordinate units require an inspected registration"
        )
    geometry = linear_svg.read(data)
    if geometry != entry["lines"]:
        raise ContentPlanError(
            "the current SVG geometry disagrees with the inspected lattice points"
        )
    lines = tuple(
        Line(g["color"], tuple(tuple(map(Fraction, p)) for p in g["points"]))
        for g in geometry
    )
    return analyze(kind, target, lines)


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    from .linear_proof import proof

    a = calculate(context, condition_asset_bytes, current_asset_content_type)
    content = _normalized_content(context)
    condition, ans, solution = (
        _section(content, k) for k in ("condition", "answer", "solution")
    )
    return finish(condition, ans, solution, answer(a.result), proof(a))
