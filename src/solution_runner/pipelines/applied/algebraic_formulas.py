"""Scalar algebraic formula models with declared economic and physical domains."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import T, answer, real_roots
from ..probability.common import UnsupportedCondition, finish
from . import common, formula_proof, inverse_proof
from .formula_questions import D, H, L, P, Q, Question, R, S, V, parse
from .inverse_patterns import KINDS as INVERSE_KINDS


@dataclass(frozen=True)
class Analysis:
    question: Question
    expression: sp.Expr
    roots: tuple
    result: sp.Rational
    domain_end: sp.Rational | None = None
    power: int | None = None
    ratio: sp.Rational | None = None


_A, _D, _G, _F, _M, _N, _S = sp.symbols("a d g f m n s", real=True)
_LAWS = {
    "thermal": (_A * Q * T, {"a": "alpha", "q": "length"}, ("alpha", "length")),
    "profit": (
        Q * (P - V) - _F,
        {"p": "price", "v": "cost", "f": "overhead"},
        ("price",),
    ),
    "market": (P * Q, {"q": "demand"}, ()),
    "bucket": (
        _M * (100 * V**2 / L - _G),
        {"l": "length", "g": "gravity"},
        ("length", "gravity"),
    ),
    "inertia": (
        (_M + 2 * _N) * R**2 / 2 + _N * (2 * R * H + H**2),
        {"m": "mass", "n": "side", "r": "radius"},
        ("mass", "side", "radius"),
    ),
    "cube": (_D * _G * L**3, {"d": "density", "g": "gravity"}, ("density", "gravity")),
    "sphere": (
        _A * _D * _G * R**3,
        {"a": "alpha", "d": "density", "g": "gravity"},
        ("alpha", "density", "gravity"),
    ),
    "stars": (_A * _S * T**4, {"a": "sigma", "s": "surface"}, ("sigma", "surface")),
    "fuse": (sp.Symbol("u", real=True) / R, {"u": "voltage"}, ("voltage",)),
    "excavator": (
        _M * _G / (2 * L * S),
        {"m": "mass", "g": "gravity", "l": "length"},
        ("mass", "gravity", "length"),
    ),
    "column": (
        4 * _M * _G / (_A * D**2),
        {"m": "mass", "g": "gravity", "a": "pi"},
        ("mass", "gravity", "pi"),
    ),
    "traction": (
        2 * _M * S / T**2,
        {"m": "mass", "s": "distance"},
        ("mass", "distance"),
    ),
}


def expected_expression(q):
    if q.kind not in _LAWS:
        raise UnsupportedCondition("an audited scalar formula family is required")
    law, bindings, positive = _LAWS[q.kind]
    if any(q.values[key] <= 0 for key in positive) or (
        q.target < 0 and q.kind != "profit"
    ):
        raise UnsupportedCondition(
            "positive coefficients and a nonnegative target are required"
        )
    if q.kind == "profit" and (q.values["cost"] < 0 or q.values["overhead"] < 0):
        raise UnsupportedCondition("nonnegative production costs are required")
    if q.kind == "market":
        demand = sp.Poly(q.demand, P)
        if demand.degree() != 1 or demand.nth(0) <= 0 or demand.nth(1) >= 0:
            raise UnsupportedCondition(
                "a positive decreasing linear demand is required"
            )
    expected = sp.expand(
        law.subs(
            {
                sp.Symbol(name, real=True): q.demand
                if key == "demand"
                else q.values[key]
                for name, key in bindings.items()
            }
        )
    )
    if sp.expand(q.expression - expected) != 0:
        raise UnsupportedCondition("the formula contradicts its declared quantities")
    return expected


def affine(q, expression):
    p = sp.Poly(expression, q.variable)
    if p.degree() != 1:
        raise UnsupportedCondition("a unique affine solution is required")
    roots = tuple(real_roots(expression - q.target, q.variable))
    result = roots[0]
    if result < 0 or (q.kind == "profit" and result.is_Integer is not True):
        raise UnsupportedCondition(
            "the requested quantity must be nonnegative and production units whole"
        )
    return Analysis(q, expression, roots, result, power=1, ratio=result)


def positive_power(q, expression):
    p = sp.Poly(expression, q.variable)
    n = p.degree()
    if n not in [1, 2, 3, 4] or p.nth(n) <= 0 or any(p.nth(i) for i in range(1, n)):
        raise UnsupportedCondition("a positive power law plus a constant is required")
    ratio = sp.simplify((q.target - p.nth(0)) / p.nth(n))
    if ratio < 0:
        raise UnsupportedCondition("the requested level has no nonnegative solution")
    result = sp.real_root(ratio, n)
    if result.is_Rational is not True:
        raise UnsupportedCondition("the exact answer must be rational without rounding")
    if q.kind == "profit" and result.is_Integer is not True:
        raise UnsupportedCondition(
            "the production quantity must be a whole number of units"
        )
    return Analysis(q, expression, (result,), result, power=n, ratio=ratio)


def market(q, expression):
    domain_end = -q.demand.subs(P, 0) / sp.diff(q.demand, P)
    roots = tuple(real_roots(expression - q.target, P))
    allowed = [r for r in roots if 0 <= r <= domain_end]
    if not allowed:
        raise UnsupportedCondition(
            "no price satisfies the requested revenue and demand"
        )
    result = max(allowed)
    if result.is_Rational is not True:
        raise UnsupportedCondition("the exact price must be rational without rounding")
    return Analysis(q, expression, roots, result, domain_end)


def inverse_power(q, expression):
    if q.target <= 0:
        raise UnsupportedCondition("a positive inverse-power threshold is required")
    denominator = sp.fraction(sp.cancel(expression))[1]
    power = sp.Poly(denominator, q.variable).degree()
    coefficient = sp.cancel(expression * q.variable**power)
    if power not in [1, 2] or coefficient.is_Rational is not True or coefficient <= 0:
        raise UnsupportedCondition("a positive inverse power is required")
    ratio = coefficient / q.target
    result = sp.real_root(ratio, power)
    if result.is_Rational is not True:
        raise UnsupportedCondition("the exact answer must be rational without rounding")
    return Analysis(q, expression, (result,), result, power=power, ratio=ratio)


def inertia(q, expression):
    roots = tuple(real_roots(expression - q.target, H))
    allowed = [r for r in roots if r >= 0]
    if q.target < expression.subs(H, 0) or len(allowed) != 1:
        raise UnsupportedCondition("no unique nonnegative radial addition is feasible")
    result = allowed[0]
    if result.is_Rational is not True:
        raise UnsupportedCondition(
            "the exact radial addition must be rational without rounding"
        )
    return Analysis(q, expression, roots, result)


def analyze(question):
    expression = expected_expression(question)
    if question.kind == "bucket":
        expression = sp.cancel(expression / sp.Symbol("m", real=True))
    if question.kind in ["thermal", "profit"]:
        return affine(question, expression)
    if question.kind == "market":
        return market(question, expression)
    if question.kind == "inertia":
        return inertia(question, expression)
    if question.kind in INVERSE_KINDS:
        return inverse_power(question, expression)
    return positive_power(question, sp.expand(expression))


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    proof = (
        inverse_proof.proof
        if analysis.question.kind in INVERSE_KINDS
        else formula_proof.proof
    )
    return finish(condition, ans, solution, answer(analysis.result), proof(analysis))
