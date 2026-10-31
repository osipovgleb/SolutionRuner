"""Positive exponential substitution and exact root selection for exam subparts."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import ScalarParser, balanced, clean

X = sp.Symbol("x", real=True)
T = sp.Symbol("t", real=True)


def polynomial(text):
    p = LaurentParser(text)
    v = symbolic(p.parse())
    if (
        p.nonzero
        or v.free_symbols - {X}
        or not v.is_polynomial(X)
        or sp.Poly(v, X).degree() > 2
    ):
        raise UnsupportedCondition(
            "the exponent must be a polynomial in x of degree at most two"
        )
    return v


def shifted(parent_html):
    candidates = []
    for s in BeautifulSoup(parent_html, "html.parser").select(
        "span[data-inline-latex]"
    ):
        raw = s["data-inline-latex"]
        probe = "".join(raw.split())
        if not (probe.startswith("t=") or probe.endswith("=t")):
            continue
        text = clean(raw)
        if text.startswith("t="):
            text = text[2:]
        elif text.endswith("=t"):
            text = text[:-2]
        else:
            continue
        m = re.match(r"\d+\^", text)
        if not m:
            continue
        raw, end = balanced(text, m.end())
        if end == len(text):
            candidates.append(polynomial(raw).subs(X, 0) != 0)
    if not candidates or len(set(candidates)) != 1:
        raise UnsupportedCondition(
            "the parent must specify one consistent exponential substitution"
        )
    return candidates[0]


def terms(formula):
    text = clean(formula)
    if text.count("=") != 1 or not text.endswith("=0"):
        raise UnsupportedCondition(
            "a complete exponential equation equal to zero is required"
        )
    text = text[:-2]
    pieces = []
    start = 0
    depth = 0
    for i, ch in enumerate(text):
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        elif ch in "+-" and depth == 0 and i > start:
            pieces.append(text[start:i])
            start = i
    pieces.append(text[start:])
    powers = []
    constant = sp.Integer(0)
    for piece in pieces:
        sign = -1 if piece.startswith("-") else 1
        piece = piece.lstrip("+-")
        m = re.match(r"(?:(\d+(?:\.\d+)?)\\cdot)?(\d+)\^", piece)
        if m:
            raw, end = balanced(piece, m.end())
            if end != len(piece):
                raise UnsupportedCondition("extra factors after an exponential term")
            coefficient = sign * ScalarParser(m[1] or "1").parse()
            base = sp.Integer(m[2])
            exponent = polynomial(raw)
            if not 1 < base <= 1000:
                raise UnsupportedCondition(
                    "a bounded base greater than one is required"
                )
            powers.append((coefficient, base, exponent))
        else:
            constant += sign * ScalarParser(piece).parse()
    if len(powers) != 2:
        raise UnsupportedCondition("exactly two exponential terms are required")
    return powers, constant


@dataclass(frozen=True)
class Analysis:
    formula: str
    base: sp.Rational
    exponent: sp.Expr
    coefficients: tuple
    t_roots: tuple
    roots: tuple
    selected: tuple
    interval: str
    bounds: tuple
    back: tuple


def analyze(formula, interval, bounds, parent_html):
    from .exam_scalar import compare

    powers, c = terms(formula)
    high, low = powers
    if high[1] != low[1] ** 2:
        raise UnsupportedCondition("the first base must be the square of the second")
    base = low[1]
    g = low[2] if shifted(parent_html) else low[2] - low[2].subs(X, 0)
    offsets = (sp.expand(2 * high[2] - 2 * g), sp.expand(low[2] - g))
    if any(
        v.free_symbols or v.is_Rational is not True or abs(v) > 100 for v in offsets
    ):
        raise UnsupportedCondition(
            "both powers must reduce to one positive substitution"
        )
    a, b = high[0] * base ** offsets[0], low[0] * base ** offsets[1]
    if any(v.is_Rational is not True for v in (a, b, c)) or a == 0:
        raise UnsupportedCondition(
            "the transformed quadratic must have exact rational coefficients"
        )
    tr = tuple(real_roots(a * T * T + b * T + c, T))
    roots = []
    back = []
    for t in tr:
        if compare(t, sp.Integer(0)) <= 0:
            continue
        value = sp.simplify(sp.expand_log(sp.log(t)) / sp.log(base))
        p = sp.Poly(g - value, X)
        if p.degree() == 1:
            branch = (sp.simplify(sp.expand_log(-p.nth(0) / p.nth(1))),)
            roots.extend(branch)
        elif p.degree() == 2 and value.is_Rational:
            branch = tuple(real_roots(p.as_expr(), X))
            roots.extend(branch)
        else:
            raise UnsupportedCondition(
                "the back-substitution must be affine or an exact rational quadratic"
            )
        back.append((t, value, branch))
    from functools import cmp_to_key

    roots = tuple(sorted(set(roots), key=cmp_to_key(compare)))
    lo, hi, lc, uc = bounds
    selected = tuple(
        r
        for r in roots
        if (compare(r, lo) > 0 or (lc and compare(r, lo) == 0))
        and (compare(r, hi) < 0 or (uc and compare(r, hi) == 0))
    )
    return Analysis(
        formula, base, g, (a, b, c), tr, roots, selected, interval, bounds, tuple(back)
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from ..word_problems.common import RepairPlan, rewrite
    from .exam_exponential_proof import render
    from .exam_input import read

    (condition, ans, solution), formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    answer, answer_html, html = render(a)
    transformations = []
    for item, key, title, expected in (
        (ans, "answer", "Ответ", answer_html),
        (solution, "solution", "Решение", html),
    ):
        if item is None or item.get("html") != expected:
            transformations.append(rewrite(item, key, title, expected))
    return RepairPlan(answer, condition["html"], html, tuple(transformations))
