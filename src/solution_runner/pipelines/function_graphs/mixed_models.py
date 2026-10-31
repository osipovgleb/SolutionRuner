"""Recover the mixed curves independently, then select the declared intersection."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import X, answer, real_roots
from ..core.errors import ContentPlanError
from ..probability.common import finish
from ..triangles.isosceles.planner import _normalized_content, _section
from . import mixed_questions, mixed_svg
from .linear_models import Line
from .parabola_models import fit

T = sp.Symbol("t", real=True)


def curve_model(kind, points):
    if kind == "parabola":
        return fit(points)
    usable = [(x, y) for x, y in points if x != 0]
    if not usable:
        raise ContentPlanError("a nonzero curve reading is required")
    x, y = usable[0]
    if kind == "root":
        if any(x < 0 for x, _ in points):
            raise ContentPlanError("the root graph requires nonnegative abscissas")
        coefficient = sp.simplify(y / sp.sqrt(x))
        expression = coefficient * sp.sqrt(X)
    elif kind == "reciprocal":
        if any(x == 0 for x, _ in points):
            raise ContentPlanError("the reciprocal graph excludes x=0")
        coefficient = x * y
        expression = coefficient / X
    else:
        raise ContentPlanError("unknown mixed curve model")
    if coefficient == 0 or any(
        sp.simplify(expression.subs(X, x) - y) != 0 for x, y in points
    ):
        raise ContentPlanError(
            "all curve readings must determine one nonzero exact coefficient"
        )
    return expression


@dataclass(frozen=True)
class Analysis:
    question: mixed_questions.Question
    entry: dict
    expression: sp.Expr
    line: Line
    roots: tuple
    root: sp.Rational
    ordinate: sp.Rational
    result: sp.Rational
    t_roots: tuple = ()


def intersections(question, expression, line):
    if question.curve_kind == "root":
        coefficient = sp.simplify(expression / sp.sqrt(X))
        t_roots = tuple(
            real_roots(line.slope * T**2 - coefficient * T + line.intercept, T)
        )
        roots = tuple(sorted({sp.simplify(t**2) for t in t_roots if t >= 0}))
    else:
        equation = line.slope * X + line.intercept - expression
        if question.curve_kind == "reciprocal":
            equation = sp.cancel(equation * X)
        roots = tuple(real_roots(equation, X))
        t_roots = ()
    if len(roots) != question.count or any(
        r.is_Rational is not True for r in roots + t_roots
    ):
        raise ContentPlanError(
            "the number of exact intersections must match the full condition"
        )
    if any(
        (question.curve_kind == "reciprocal" and r == 0)
        or sp.simplify(expression.subs(X, r) - line.value(r)) != 0
        for r in roots
    ):
        raise ContentPlanError(
            "each intersection must satisfy the original unsquared equations"
        )
    return roots, t_roots


def analyze(question, entry, marked):
    cp = [tuple(map(sp.Rational, p)) for p in entry["curve_points"]]
    lp = tuple(tuple(map(sp.Rational, p)) for p in entry["line_points"])
    if len(lp) != 2:
        raise ContentPlanError("two line readings are required")
    line = Line(entry["line_color"], lp)
    if line.slope == 0:
        raise ContentPlanError("the inspected mixed methods require an oblique line")
    expression = curve_model(question.curve_kind, cp)
    if (
        question.known_line is not None
        and sp.expand(question.known_line - (line.slope * X + line.intercept)) != 0
    ):
        raise ContentPlanError(
            "the specified line must agree with the inspected drawing"
        )
    if question.line_origin and line.intercept != 0:
        raise ContentPlanError("the declared line kx must pass through the origin")
    for x, y, color in marked:
        value = (
            expression.subs(X, x) if color == entry["curve_color"] else line.value(x)
        )
        if sp.simplify(value - y) != 0:
            raise ContentPlanError(
                "every visible colored marker must agree with its recovered function"
            )
    roots, t_roots = intersections(question, expression, line)
    if question.count == 2:
        visible = entry.get("visible_a")
        if not visible or tuple(visible) not in cp or tuple(visible) not in lp:
            raise ContentPlanError("the inspected A must be a common graph reading")
        ax, ay = map(sp.Rational, visible)
        if ax not in roots or line.value(ax) != ay:
            raise ContentPlanError(
                "the inspected A must identify exactly one valid root"
            )
        root = next(r for r in roots if r != ax)
    else:
        if entry.get("visible_a") is not None:
            raise ContentPlanError(
                "the unique-intersection method needs its own inspected diagram"
            )
        root = roots[0]
    ordinate = sp.simplify(line.value(root))
    result = root if question.coordinate == "x" else ordinate
    if result.is_Rational is not True:
        raise ContentPlanError("the requested mixed intersection must be rational")
    return Analysis(
        question, entry, expression, line, roots, root, ordinate, result, t_roots
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    from .mixed_proof import proof

    question = mixed_questions.parse(context)
    entry, marked = mixed_svg.read(
        context, condition_asset_bytes, current_asset_content_type, question.curve_kind
    )
    a = analyze(question, entry, marked)
    content = _normalized_content(context)
    condition, ans, solution = (
        _section(content, k) for k in ("condition", "answer", "solution")
    )
    return finish(condition, ans, solution, answer(a.result), proof(a))
