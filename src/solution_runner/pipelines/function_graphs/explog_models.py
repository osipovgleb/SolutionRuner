"""Recover exact bases and shifts from independently read graph coordinates."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..core.errors import ContentPlanError
from ..probability.common import finish
from ..triangles.isosceles.planner import _normalized_content, _section
from . import explog_questions, explog_svg

A = sp.Symbol("a", positive=True)


def exact_log(value, base):
    if value <= 0 or base <= 0 or base == 1:
        raise ContentPlanError("a logarithm needs a positive argument and a valid base")
    exponent = sp.simplify(
        sp.expand_log(sp.log(value), force=True)
        / sp.expand_log(sp.log(base), force=True)
    )
    if exponent.is_Rational is not True or sp.simplify(base**exponent - value) != 0:
        raise ContentPlanError(
            "an exact rational logarithm must follow from matching powers"
        )
    return exponent


def positive_base(expression):
    poly = sp.Poly(sp.together(expression).as_numer_denom()[0], A)
    if not 1 <= poly.degree() <= 4 or any(
        c.is_Rational is not True for c in poly.all_coeffs()
    ):
        raise ContentPlanError(
            "the inspected base equation must have degree at most four"
        )
    roots = {
        r
        for r in sp.real_roots(poly)
        if r.is_positive is True and r != 1 and sp.simplify(expression.subs(A, r)) == 0
    }
    if len(roots) != 1:
        raise ContentPlanError(
            "the marked points must determine one positive base different from 1"
        )
    return roots.pop(), poly.as_expr()


@dataclass(frozen=True)
class Analysis:
    question: explog_questions.Question
    points: list
    base: sp.Expr
    shift: sp.Expr
    equation: sp.Expr | None
    result: sp.Rational
    entry: dict


def plain_parameters(model, points):
    candidates = (
        [p for p in points if p[0] != 0]
        if model == "exp_plain"
        else [p for p in points if p[1] != 0]
    )
    if not candidates:
        raise ContentPlanError(
            "a nontrivial graph point is required to recover the base"
        )
    x, y = min(
        candidates,
        key=lambda p: (abs(p[0] if model == "exp_plain" else p[1]), -p[0]),
    )
    if (model == "exp_plain" and y <= 0) or (model == "log_plain" and x <= 0):
        raise ContentPlanError("the graph point is outside the model's domain or range")
    base = y ** (1 / x) if model == "exp_plain" else x ** (1 / y)
    return sp.simplify(base), sp.Integer(0), None, [(x, y)]


def logarithmic_vertical_parameters(pair):
    (x1, y1), (x2, y2) = pair
    if min(x1, x2) <= 0:
        raise ContentPlanError("the logarithmic graph needs positive abscissas")
    base = sp.simplify((x2 / x1) ** (1 / (y2 - y1)))
    return base, sp.simplify(y1 - exact_log(x1, base)), None, pair


def exponential_horizontal_parameters(pair):
    (x1, y1), (x2, y2) = pair
    if min(y1, y2) <= 0:
        raise ContentPlanError("the exponential graph needs positive ordinates")
    base = sp.simplify((y2 / y1) ** (1 / (x2 - x1)))
    return base, sp.simplify(exact_log(y1, base) - x1), None, pair


def polynomial_parameters(model, pair):
    (x1, y1), (x2, y2) = pair
    if model == "log_horizontal":
        if any(y.is_Integer is not True or not 0 <= y <= 3 for _, y in pair):
            raise ContentPlanError(
                "the logarithmic point system requires inspected powers 0 through 3"
            )
        base, equation = positive_base(A**y2 - A**y1 - (x2 - x1))
        return base, sp.simplify(base**y1 - x1), equation, pair
    if model == "exp_vertical":
        if any(x.is_Integer is not True or abs(x) > 4 for x, _ in pair):
            raise ContentPlanError(
                "the exponential point system requires inspected integer powers"
            )
        base, equation = positive_base(A**x2 - A**x1 - (y2 - y1))
        return base, sp.simplify(y1 - base**x1), equation, pair
    raise ContentPlanError("unknown exponential or logarithmic graph model")


def parameters(model, points):
    if model in {"exp_plain", "log_plain"}:
        return plain_parameters(model, points)
    if len(points) < 2:
        raise ContentPlanError("two independently read coordinates are required")
    pair = points[:2]
    (x1, y1), (x2, y2) = pair
    if x1 == x2 or y1 == y2:
        raise ContentPlanError(
            "the graph points must have different abscissas and ordinates"
        )
    readers = {
        "log_vertical": logarithmic_vertical_parameters,
        "exp_horizontal": exponential_horizontal_parameters,
    }
    if model in readers:
        return readers[model](pair)
    return polynomial_parameters(model, pair)


def function(model, base, shift, x):
    if model.startswith("exp"):
        return sp.simplify(
            base ** (x + shift) if model == "exp_horizontal" else base**x + shift
        )
    return (
        exact_log(x + shift, base)
        if model == "log_horizontal"
        else shift + exact_log(x, base)
    )


def analyze(question, points, entry):
    model = question.model
    base, shift, equation, pair = parameters(model, points)
    if base.is_positive is not True or base == 1:
        raise ContentPlanError(
            "the function base must be positive and different from 1"
        )
    if any(sp.simplify(function(model, base, shift, x) - y) != 0 for x, y in points):
        raise ContentPlanError(
            "every inspected graph point must agree with the recovered formula"
        )
    if model == "log_horizontal" and entry.get("vertical_asymptote") != -shift:
        raise ContentPlanError(
            "the inspected vertical asymptote must agree with the point system"
        )
    if model == "exp_vertical" and entry.get("horizontal_asymptote") != shift:
        raise ContentPlanError(
            "the inspected horizontal asymptote must agree with the point system"
        )
    target = question.target
    if question.mode == "value":
        result = function(model, base, shift, target)
    elif model.startswith("log"):
        result = sp.simplify(
            base**target - shift
            if model == "log_horizontal"
            else base ** (target - shift)
        )
    else:
        result = (
            exact_log(target, base) - shift
            if model == "exp_horizontal"
            else exact_log(target - shift, base)
        )
    if result.is_Rational is not True:
        raise ContentPlanError(
            "the requested graph value must have an exact rational answer"
        )
    if (
        question.mode == "argument"
        and sp.simplify(function(model, base, shift, result) - target) != 0
    ):
        raise ContentPlanError(
            "the inverse result must satisfy the original graph formula"
        )
    return Analysis(question, pair, base, shift, equation, result, entry)


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    from .explog_proof import proof

    question = explog_questions.parse(context)
    entry, points, _ = explog_svg.read(
        context, condition_asset_bytes, current_asset_content_type, question.model
    )
    analysis = analyze(question, points, entry)
    content = _normalized_content(context)
    condition, ans, solution = (
        _section(content, key) for key in ("condition", "answer", "solution")
    )
    return finish(condition, ans, solution, answer(analysis.result), proof(analysis))
