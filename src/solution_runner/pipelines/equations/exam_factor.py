"""Solve factorable exponential polynomials and polynomial-product branches."""

from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import Analysis, T, X, back_substitute, polynomial, select_roots
from .exam_power_polynomial import normalize
from .exam_power_terms import read as terms
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class FactorAnalysis:
    equation: Analysis
    normalized: sp.Expr
    transformed: sp.Expr
    factored: sp.Expr
    algebraic: sp.Expr | None
    algebraic_roots: tuple
    alternate: bool


def split_product(formula):
    text = clean(formula)
    if not text.startswith("("):
        return formula, None
    left, end = balanced(text, 0, "(", ")")
    if text[end : end + 1] != "(":
        return formula, None
    right, end = balanced(text, end, "(", ")")
    if text[end:] != "=0":
        raise UnsupportedCondition(
            "a polynomial-product equation must end exactly at zero"
        )
    p = polynomial(left)
    if sp.Poly(p, X).degree() not in (1, 2):
        raise UnsupportedCondition(
            "the separate polynomial factor must be affine or quadratic"
        )
    return right + "=0", p


def factor_roots(expression):
    roots = []
    for factor, _multiplicity in sp.factor_list(expression, T)[1]:
        if sp.Poly(factor, T).degree() > 2:
            raise UnsupportedCondition(
                "the exponential polynomial must factor into linear or quadratic real equations"
            )
        roots.extend(real_roots(factor, T))
    return tuple(sorted(set(roots), key=sp.default_sort_key))


def parent_methods(html):
    soup = BeautifulSoup(html, "html.parser")
    lists = soup.select('ol[data-layout="source-subparts"]')
    if (
        len(lists) != 1
        or len(lists[0].find_all("li", recursive=False)) != 2
        or not soup.select("[data-inline-latex]")
    ):
        raise UnsupportedCondition("one audited two-part parent solution is required")
    text = soup.get_text(" ", strip=True).replace("\xad", "").replace("ё", "е")
    alternate = "Примечание." in text and "замену" in text and "множители" in text
    return alternate


def analyze(formula, interval, bounds, parent_html):
    alternate = parent_methods(parent_html)
    exponential, algebraic = split_product(formula)
    powers, constant = terms(exponential)
    base, g, normalized, divisor = normalize(powers, constant)
    transformed = primitive(normalized, (T,))
    if sp.Poly(transformed, T).degree() < 1:
        raise UnsupportedCondition(
            "the reduced exponential equation must remain nonconstant"
        )
    tr = factor_roots(transformed)
    if not tr:
        raise UnsupportedCondition(
            "the supported factorization must expose real branches"
        )
    roots, back = back_substitute(base, g, tr)
    polynomial_roots = tuple(real_roots(algebraic, X)) if algebraic is not None else ()
    roots, selected = select_roots((*roots, *polynomial_roots), bounds)
    coefficients = tuple(sp.Poly(normalized, T).all_coeffs())
    a = Analysis(
        formula,
        base,
        g,
        coefficients,
        tr,
        roots,
        selected,
        interval,
        bounds,
        tuple(back),
        divisor,
        False,
    )
    factorization = sp.factor(transformed)
    p = sp.Poly(transformed, T)
    if p.degree() == 3:
        A, B, C, D = p.all_coeffs()
        if D * A == B * C:
            factorization = sp.Mul(A, T + B / A, T * T + C / A, evaluate=False)
    return FactorAnalysis(
        a,
        normalized,
        transformed,
        factorization,
        algebraic,
        polynomial_roots,
        alternate,
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_factor_proof import render
    from .exam_input import read, repair

    parts, formula, interval, bounds = read(context)
    result = analyze(formula, interval, bounds, parent_solution_html)
    return repair(parts, *render(result))
