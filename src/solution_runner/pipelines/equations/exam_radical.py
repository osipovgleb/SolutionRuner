"""Isolate reviewed radicals, retain signs, and solve finite polynomial branches."""

from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import polynomial, real_roots
from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X, select_roots
from .exam_rational import Selection
from .exam_scalar import compare
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import balanced, clean

Z, W = sp.symbols("z w", real=True)


@dataclass(frozen=True)
class Analysis:
    selection: Selection
    radicands: tuple
    right: sp.Expr
    multiplier: sp.Expr
    equation: sp.Expr
    candidates: tuple
    method: str
    alternative: bool


def candidates(expression):
    if expression == 0:
        raise UnsupportedCondition("an identity requires an infinite solution set")
    _, factors = sp.factor_list(expression, X)
    result = []
    for factor, _ in factors:
        result.extend(real_roots(factor, X))
    return tuple(dict.fromkeys(result))


def read_equation(formula):
    text = clean(formula)
    if text.count("=") != 1 or any(c in text for c in "zw"):
        raise UnsupportedCondition("one radical equation in x is required")
    radicands = []
    while r"\sqrt" in text:
        start = text.index(r"\sqrt")
        inside, end = balanced(text, start + 5)
        if len(radicands) >= 2 or r"\sqrt" in inside:
            raise UnsupportedCondition(
                "at most two unnested polynomial radicals are supported"
            )
        radicands.append(polynomial(inside, X))
        text = text[:start] + "zw"[len(radicands) - 1] + text[end:]
    values = []
    for part in text.split("="):
        parser = LaurentParser(part)
        value = symbolic(parser.parse())
        if (
            parser.nonzero
            or value.free_symbols - {X, Z, W}
            or not value.is_polynomial(X, Z, W)
        ):
            raise UnsupportedCondition(
                "the radical equation must have polynomial operands without poles"
            )
        values.append(value)
    return tuple(radicands), sp.expand(values[0] - values[1])


def single_method(p, right, parent, alternative):
    c = p.subs(X, 0)
    symmetric = sp.expand(p - X - c) == 0 and sp.expand(right - X**2 + c) == 0
    if symmetric:
        if (
            c.is_Rational is not True
            or c <= 0
            or not all(
                s in parent
                for s in (
                    "суммой",
                    "другое решение",
                    "еще одно решение",
                    "квадратное относительно",
                )
            )
        ):
            raise UnsupportedCondition(
                "the symmetric parent must retain all three reviewed methods"
            )
        method = "symmetric"
    else:
        if (
            sp.Poly(right, X).degree() > 1
            or sp.Poly(p, X).degree() > 3
            or "неотрицательны" in parent
        ):
            raise UnsupportedCondition(
                "squaring needs a polynomial radicand and an affine right side"
            )
        if not any(
            s in parent for s in ("не имеет корней", "воспользуемся", "решим уравнение")
        ):
            raise UnsupportedCondition(
                "the parent must preserve the sign before squaring"
            )
        if alternative and (
            sp.Poly(p, X).degree() != 1
            or sp.Poly(p, X).nth(1) <= 0
            or "примечание" not in parent
        ):
            raise UnsupportedCondition(
                "the alternative substitution requires one increasing affine radicand"
            )
        method = "single"
    return method


def analyze(formula, interval, bounds, parent_html):
    radicands, expression = read_equation(formula)
    parent = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .lower()
    )
    if not parent or len(radicands) not in (1, 2):
        raise UnsupportedCondition(
            "a reviewed parent solution with radicals is required"
        )
    alternative = "другое решение" in parent
    if len(radicands) == 2:
        if (
            expression not in (Z - W, W - Z)
            or "подкоренные выражения" not in parent
            or alternative
        ):
            raise UnsupportedCondition("the parent must equate nonnegative radicands")
        p, q = radicands
        right, equation, method = sp.Integer(0), sp.expand(p - q), "equal"
    else:
        p = radicands[0]
        coefficient = expression.coeff(Z)
        if (
            coefficient.is_Rational is not True
            or coefficient == 0
            or sp.expand(expression - coefficient * Z).has(Z, W)
        ):
            raise UnsupportedCondition(
                "one radical with a nonzero rational multiplier is required"
            )
        right = sp.expand(-(expression - coefficient * Z) / coefficient)
        equation = sp.expand(p - right**2)
        method = single_method(p, right, parent, alternative)
    proposed = candidates(equation)
    accepted = []
    for r in proposed:
        values = [sp.simplify(p.subs(X, r)) for p in radicands]
        valid = all(compare(v, sp.Integer(0)) >= 0 for v in values)
        if method != "equal":
            valid = valid and compare(sp.simplify(right.subs(X, r)), sp.Integer(0)) >= 0
        if valid:
            accepted.append(r)
    roots, selected = select_roots(accepted, bounds)
    return Analysis(
        Selection(roots, selected, interval, bounds),
        radicands,
        right,
        abs(coefficient) if len(radicands) == 1 else sp.Integer(1),
        equation,
        proposed,
        method,
        alternative,
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_input import read, repair
    from .exam_radical_proof import render

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    return repair(parts, *render(a))
