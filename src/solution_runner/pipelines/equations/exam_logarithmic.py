"""Reduce reviewed logarithms with their original strict argument domains."""

from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from .exam_exponential import T, X, select_roots
from .exam_logarithmic_input import read_equation
from .exam_radical import candidates
from .exam_rational import Selection
from .exam_scalar import compare
from .logarithm_arithmetic import log_ratio, power


@dataclass(frozen=True)
class Analysis:
    selection: Selection
    atoms: tuple
    expression: sp.Expr
    method: str
    base: sp.Expr
    equation: sp.Expr
    candidates: tuple
    effective: tuple
    replacements: tuple = ()
    back: tuple = ()


def linear(expression, atoms):
    coefficients = tuple(expression.coeff(a.symbol) for a in atoms)
    constant = expression.subs({a.symbol: 0 for a in atoms})
    if (
        constant.is_Rational is not True
        or any(c.is_Rational is not True or c == 0 for c in coefficients)
        or sp.expand(
            expression
            - constant
            - sum(c * a.symbol for c, a in zip(coefficients, atoms))
        )
        != 0
    ):
        raise UnsupportedCondition(
            "the complete equation must be affine in each original logarithm"
        )
    return coefficients, constant


def simple(atoms, expression):
    atom = atoms[0]
    (coefficient,), constant = linear(expression, atoms)
    value = -constant / coefficient
    if (
        atom.root
        or sp.Poly(atom.argument, X).degree() > 2
        or value.is_Rational is not True
    ):
        raise UnsupportedCondition(
            "one logarithm of a quadratic and a rational level are required"
        )
    target = power(atom.base, value)
    if target.is_Rational is not True:
        raise UnsupportedCondition("the reviewed exponential level must be rational")
    equation = sp.expand(atom.argument - target)
    return "simple", atom.base, equation, (value, target), (), ()


def common_base(atoms, expression):
    coefficients, constant = linear(expression, atoms)
    if (
        len(atoms) != 2
        or coefficients[0] != -coefficients[1]
        or abs(coefficients[0]) != 1
    ):
        raise UnsupportedCondition(
            "two logarithms must occur with opposite unit coefficients"
        )
    for i, j in ((0, 1), (1, 0)):
        left, right = atoms[i], atoms[j]
        if (
            right.base == left.base**2
            and right.argument == X**4
            and not (left.root or right.root)
            and constant == 0
            and sp.Poly(left.argument, X).degree() == 1
        ):
            return (
                "base-square",
                left.base,
                sp.expand(X * X - left.argument),
                (left.argument, X * X),
                (),
                (),
            )
        if (
            left.base.is_Rational
            and right.base**2 == left.base
            and right.root
            and not left.root
        ):
            shift = constant / coefficients[i]
            factor = power(left.base, shift)
            if factor.is_Rational is not True:
                raise UnsupportedCondition(
                    "the additive logarithm shift must give a rational scale"
                )
            reduced = sp.expand(right.argument / factor)
            equation = sp.expand(reduced - left.argument)
            if sp.Poly(equation, X).degree() > 4:
                raise UnsupportedCondition(
                    "the common-base equation must have degree at most four"
                )
            return (
                "root-base",
                left.base,
                equation,
                (left.argument, reduced, shift, right.argument),
                (),
                (),
            )
    raise UnsupportedCondition(
        "the reviewed squared or square-root base relation is required"
    )


def monomial(atom, base):
    if atom.base != base or atom.root:
        raise UnsupportedCondition(
            "the logarithm substitution needs one common base and no argument roots"
        )
    terms = sp.Poly(atom.argument, X).terms()
    if len(terms) != 1:
        raise UnsupportedCondition(
            "each substituted logarithm needs one positive monomial argument"
        )
    (degree,), coefficient = terms[0]
    if coefficient <= 0 or not 1 <= degree <= 4:
        raise UnsupportedCondition(
            "the logarithm monomial needs a positive coefficient and degree"
        )
    shift = log_ratio(base, coefficient)
    if shift.is_Rational is not True:
        raise UnsupportedCondition(
            "the monomial coefficient must have a rational logarithm"
        )
    return degree, sp.expand(degree * T + shift)


def quadratic(atoms, expression):
    base = atoms[0].base
    forms = tuple(monomial(a, base) for a in atoms)
    if not any(degree % 2 for degree, _ in forms):
        raise UnsupportedCondition(
            "an odd positive monomial must justify x greater than zero"
        )
    replacements = tuple(f for _, f in forms)
    equation = sp.expand(
        expression.subs(
            {a.symbol: f for a, f in zip(atoms, replacements)}, simultaneous=True
        )
    )
    if sp.Poly(equation, T).degree() != 2:
        raise UnsupportedCondition(
            "the reviewed substitution must give a quadratic equation in t"
        )
    levels = real_roots(equation, T)
    if any(t.is_Rational is not True for t in levels):
        raise UnsupportedCondition(
            "the logarithm back-substitution requires rational levels"
        )
    back = tuple((t, sp.simplify(power(base, t))) for t in levels)
    return "quadratic", base, equation, (), replacements, back


def analyze(formula, interval, bounds, parent_html):
    atoms, expression = read_equation(formula)
    soup = BeautifulSoup(parent_html, "html.parser")
    text = soup.get_text(" ", strip=True).replace("\xad", "").lower()
    if not text or "другое решение" in text or "еще одно решение" in text:
        raise UnsupportedCondition("one complete reviewed parent method is required")
    substitution = any(
        "".join(s["data-inline-latex"].split()).startswith(r"t=\log_")
        for s in soup.select("[data-inline-latex]")
    )
    if substitution:
        result = quadratic(atoms, expression)
    elif len(atoms) == 1 and "из уравнения получаем" in text:
        result = simple(atoms, expression)
    elif len(atoms) == 2 and any(
        s in text for s in ("запишем исходное уравнение", "получаем")
    ):
        result = common_base(atoms, expression)
    else:
        raise UnsupportedCondition(
            "the logarithm method must match the reviewed parent"
        )
    method, base, equation, effective, replacements, back = result
    proposed = (
        tuple(r for _, r in back)
        if back
        else (() if method == "quadratic" else candidates(equation))
    )
    roots = []
    for r in proposed:
        if all(
            compare(sp.simplify(a.argument.subs(X, r)), sp.Integer(0)) > 0
            for a in atoms
        ):
            roots.append(r)
    roots, selected = select_roots(roots, bounds)
    return Analysis(
        Selection(roots, selected, interval, bounds),
        atoms,
        expression,
        method,
        base,
        equation,
        proposed,
        effective,
        replacements,
        back,
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_input import repair
    from .exam_logarithmic_input import read
    from .exam_logarithmic_proof import render

    parts, formula, interval, bounds = read(context)
    return repair(
        parts, *render(analyze(formula, interval, bounds, parent_solution_html))
    )
