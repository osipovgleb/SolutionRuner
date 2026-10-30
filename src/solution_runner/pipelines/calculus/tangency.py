"""Polynomial contact conditions distinguish a tangent from a parallel line."""

import re
from dataclasses import dataclass

import sympy as sp

from ..equations.power_arithmetic import clean
from ..probability.common import UnsupportedCondition, finish
from .common import X, answer, polynomial, read, real_roots


@dataclass
class Contact:
    condition: dict
    answer_section: dict | None
    solution: dict | None
    line: sp.Expr
    curve: sp.Expr
    parallel: bool
    quantity: str
    parameter: sp.Symbol | None
    sign: int | None
    candidates: list
    valid: list
    result: sp.Expr


def _read(context):
    condition, current_answer, solution, text = read(context)
    match = re.fullmatch(
        r"Прямая (?P<line>.+?) (?P<kind>параллельна касательной|является касательной) к графику функции (?P<curve>.+?)\. Найдите (?P<request>.+)\.",
        text,
    )
    if not match:
        raise UnsupportedCondition("unsupported complete analytic tangent question")
    line_text = clean(match["line"])
    curve_text = clean(match["curve"])
    if not line_text.startswith("y="):
        raise UnsupportedCondition("the given line must be explicit y=kx+b")
    line = polynomial(line_text[2:], X)
    if sp.Poly(line, X).degree() > 1:
        raise UnsupportedCondition("the comparison graph is not a straight line")
    parallel = match["kind"] == "параллельна касательной"
    request = match["request"]
    parameter = None
    sign = None
    if request in ["абсциссу точки касания", "ординату точки касания"]:
        quantity = "x" if request.startswith("абсциссу") else "y"
    else:
        choice = re.fullmatch(
            r"([abc])(?:, учитывая, что абсцисса точки касания (больше|меньше) 0)?",
            request,
        )
        if not choice or parallel:
            raise UnsupportedCondition(
                "one contact coordinate or one parameter must be requested"
            )
        quantity = "parameter"
        parameter = sp.Symbol(choice[1], real=True)
        if choice[2]:
            sign = 1 if choice[2] == "больше" else -1
    curve_text = re.sub(r"^(?:y|f\(x\))=", "", curve_text)
    curve = polynomial(curve_text, X, () if parameter is None else (parameter.name,))
    return Contact(
        condition,
        current_answer,
        solution,
        line,
        curve,
        parallel,
        quantity,
        parameter,
        sign,
        [],
        [],
        sp.Integer(0),
    )


def _parameter_candidates(contact):
    a, b, c = (sp.expand(contact.curve).coeff(X, p) for p in [2, 1, 0])
    k, l = sp.diff(contact.line, X), contact.line.subs(X, 0)
    parameter = contact.parameter
    if sp.expand(
        contact.curve - a * X * X - b * X - c
    ) != 0 or contact.curve.free_symbols != {X, parameter}:
        raise UnsupportedCondition(
            "the parameter must occur in one quadratic polynomial"
        )
    if a == parameter and not b.free_symbols and not c.free_symbols:
        delta = k - b
        if delta == 0 or c == l:
            raise UnsupportedCondition(
                "the leading parameter is inconsistent or underdetermined"
            )
        x0 = 2 * (c - l) / delta
        values = [(x0, delta / (2 * x0))]
    elif b == parameter and a.is_Rational is True and a != 0 and c.is_Rational is True:
        values = [
            (root, k - 2 * a * root) for root in real_roots(X * X - (c - l) / a, X)
        ]
    elif c == parameter and a.is_Rational is True and a != 0 and b.is_Rational is True:
        x0 = (k - b) / (2 * a)
        values = [(x0, l + a * x0 * x0)]
    else:
        raise UnsupportedCondition(
            "the reviewed parameter occupies one quadratic coefficient"
        )
    return [(sp.simplify(x), sp.simplify(p)) for x, p in values]


def calculate(context):
    contact = _read(context)
    derivative = sp.diff(contact.curve, X)
    slope = sp.diff(contact.line, X)
    if contact.parameter is None:
        contact.candidates = real_roots(derivative - slope, X)
        contact.valid = [
            x
            for x in contact.candidates
            if contact.parallel
            or sp.simplify((contact.curve - contact.line).subs(X, x)) == 0
        ]
        if len(contact.valid) != 1:
            raise UnsupportedCondition(
                "the question does not determine one contact point"
            )
        x0 = contact.valid[0]
        contact.result = (
            x0 if contact.quantity == "x" else sp.simplify(contact.line.subs(X, x0))
        )
    else:
        contact.candidates = _parameter_candidates(contact)
        for x0, p in contact.candidates:
            if contact.sign is not None and sp.sign(x0) != contact.sign:
                continue
            curve = contact.curve.subs(contact.parameter, p)
            if (
                sp.simplify(sp.diff(curve, X).subs(X, x0) - slope) == 0
                and sp.simplify((curve - contact.line).subs(X, x0)) == 0
            ):
                contact.valid.append((x0, p))
        values = {p for _, p in contact.valid}
        if len(values) != 1:
            raise UnsupportedCondition(
                "the contact conditions leave no unique admissible parameter"
            )
        contact.result = values.pop()
    return contact


def build_context_repair_plan(context, *, two_methods=False):
    from .tangency_proof import render

    contact = calculate(context)
    return finish(
        contact.condition,
        contact.answer_section,
        contact.solution,
        answer(contact.result),
        render(contact, two_methods=two_methods),
    )
