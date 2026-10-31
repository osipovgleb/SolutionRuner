"""Exact interpolation, coefficient checks and the other intersection after A."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import X, answer, real_roots
from ..core.errors import ContentPlanError
from ..probability.common import finish
from ..triangles.isosceles.planner import _normalized_content, _section
from . import parabola_questions, parabola_svg
from .linear_svg import NS, snap
from .parabola_questions import PARAMETERS

ASSET_DIR = Path(__file__).parent / "assets/parabolas"


def registry():
    return json.loads((ASSET_DIR / "source-evidence.json").read_text())


def fit(points):
    if len(points) < 3 or len({p[0] for p in points}) != len(points):
        raise ContentPlanError("three distinct inspected abscissas are required")
    expression = sp.interpolate([tuple(map(sp.Rational, p)) for p in points], X)
    p = sp.Poly(expression, X)
    if p.degree() != 2 or any(p.nth(i).is_Rational is not True for i in range(3)):
        raise ContentPlanError(
            "the inspected points must define one nondegenerate quadratic"
        )
    return p.as_expr()


@dataclass(frozen=True)
class Analysis:
    question: parabola_questions.Question
    curve: dict
    expression: sp.Expr
    roots: tuple = ()
    root: sp.Rational | None = None
    visible_a: sp.Rational | None = None
    result: sp.Rational | None = None


def other_intersection(question, curve, expression, root, axes, entry):
    roots = tuple(real_roots(question.given - expression, X))
    if (
        len(roots) != 2
        or any(r.is_Rational is not True for r in roots)
        or entry.get("visible_intersection_label") != "A"
    ):
        raise ContentPlanError(
            "two rational intersections and the inspected visible label A are required"
        )
    xmap, ymap, sx, sy = axes
    markers = {
        (snap(float(n.get("cx")), xmap, sx), snap(float(n.get("cy")), ymap, sy))
        for n in root.iter(NS + "circle")
    }
    visible = [r for r in roots if (r, expression.subs(X, r)) in markers]
    if len(visible) != 1:
        raise ContentPlanError(
            "one marked visible A must distinguish the other intersection B"
        )
    sought = next(r for r in roots if r != visible[0])
    result = sought if question.kind == "intersection_x" else expression.subs(X, sought)
    return Analysis(question, curve, expression, roots, sought, visible[0], result)


def analyze(question, entry, data):
    root, axes = parabola_svg.read(data, entry)
    if question.kind == "value":
        if len(entry["curves"]) != 1:
            raise ContentPlanError(
                "one quadratic graph is required for a function value"
            )
        curve = entry["curves"][0]
        expression = fit(curve["points"])
        if any(expression.subs(X, p[0]) != p[1] for p in curve["marked_points"]):
            raise ContentPlanError(
                "all marked points must agree with the reconstructed polynomial"
            )
        p = sp.Poly(expression, X)
        values = {
            symbol: p.nth(i) for symbol, i in zip(PARAMETERS, (2, 1, 0), strict=True)
        }
        if any(values[symbol] != value for symbol, value in question.fixed.items()):
            raise ContentPlanError(
                "the stated coefficient disagrees with the inspected graph"
            )
        if question.whole and any(
            value.is_Integer is not True for value in values.values()
        ):
            raise ContentPlanError("all declared integer coefficients must be integral")
        return Analysis(
            question, curve, expression, result=expression.subs(X, question.target)
        )
    matching = [
        c
        for c in entry["curves"]
        if all(
            question.given.subs(X, p[0]) == p[1]
            for p in c["points"] + c["marked_points"]
        )
    ]
    if len(entry["curves"]) != 2 or len(matching) != 1:
        raise ContentPlanError(
            "the specified polynomial must identify exactly one pictured parabola"
        )
    curve = next(c for c in entry["curves"] if c is not matching[0])
    expression = fit(curve["points"])
    if any(expression.subs(X, p[0]) != p[1] for p in curve["marked_points"]):
        raise ContentPlanError(
            "all marked points must agree with the reconstructed polynomial"
        )
    return other_intersection(question, curve, expression, root, axes, entry)


def calculate(context, data, mime):
    question = parabola_questions.parse(context)
    content = _normalized_content(context)
    if (
        len(content["assets"]) != 1
        or str(mime).split(";")[0].lower() != "image/svg+xml"
        or not data
    ):
        raise ContentPlanError("one inspected parabola SVG is required")
    if any(
        s.get("asset_keys")
        or BeautifulSoup(s.get("html", ""), "html.parser").select(
            "img, [data-asset-id], [data-asset-key]"
        )
        for s in content["sections"]
        if s.get("key") != "condition"
    ):
        raise ContentPlanError(
            "these quadratic methods use only the original condition image"
        )
    entry = registry().get(hashlib.sha256(data).hexdigest())
    if not entry or entry["grid_unit"] != [1, 1]:
        raise ContentPlanError(
            "the parabola bytes and coordinate units need an inspected registration"
        )
    return analyze(question, entry, data)


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    from .parabola_proof import proof

    a = calculate(context, condition_asset_bytes, current_asset_content_type)
    content = _normalized_content(context)
    condition, ans, solution = (
        _section(content, k) for k in ("condition", "answer", "solution")
    )
    return finish(condition, ans, solution, answer(a.result), proof(a))
