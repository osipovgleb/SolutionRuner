"""Retain the original logarithm domain and the shared zero of both factors."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import (
    compare,
    monomial,
    read_terms,
    vector,
    weight,
)
from .exponential_inequality_proof import power
from .exponential_log_product_input import ExponentialLogProductParser
from .rational_inequality import accepts, set_latex
from .rational_inequality_methods import terms
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison
from .variable_logarithm_parser import Atoms


@dataclass(frozen=True)
class ExponentialLogProduct:
    operator: str
    base: sp.Expr
    argument: sp.Expr
    shift: sp.Expr
    exponents: tuple
    log_polynomial: sp.Expr
    log_stage: object
    domain: object
    shared_zero: sp.Expr
    second_zero: sp.Expr
    level: sp.Expr
    points: tuple
    signs: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def exponential_comparison(node):
    pieces = []
    for sign, term in terms(node):
        coefficient, term_power = monomial(term)
        text = sp.latex(coefficient)
        if term_power is not None:
            text += r"\cdot " + power(*term_power)
        pieces.append(("+" if sign > 0 else "-") + text)
    return compare("".join(pieces) + r"\gt0")


def read_product(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: ExponentialLogProductParser(text, atoms=atoms)
    )
    if (
        left.kind != "multiply"
        or right.kind != "scalar"
        or right.value != 0
        or len(atoms.values) != 2
        or any(d.free_symbols for d in denominators)
    ):
        raise UnsupportedCondition(
            "one complete product of exponential and logarithmic factors with no original poles is required"
        )
    exponential, logarithmic = left.children
    if exponential.value.free_symbols - {X} or logarithmic.value.free_symbols - {
        a.symbol for a in atoms.values
    }:
        raise UnsupportedCondition(
            "all exponentials and all logarithms must belong to their respective complete factors"
        )
    e = exponential_comparison(exponential)
    if any(polynomial(p).degree() != 1 for p in e.exponents) or len(e.stage.zeros) != 1:
        raise UnsupportedCondition(
            "the exponential factor must have one affine sign transition"
        )
    return operator, e, logarithmic, atoms.values


def logarithm_factor(logarithmic, atoms, base):
    first, second = atoms
    p = polynomial(first.argument)
    if (
        first.argument != second.argument
        or p.degree() != 1
        or p.LC() != 1
        or p.nth(0).is_Rational is not True
        or abs(p.nth(0)) > 1000
    ):
        raise UnsupportedCondition(
            "both logarithms require the same monic affine argument"
        )
    shift = p.nth(0)
    replacements = {}
    for atom in atoms:
        degree = weight(atom.base, vector(base))
        if degree == 0 or abs(degree) > 4 or atom.root:
            raise UnsupportedCondition(
                "logarithm bases must be nontrivial bounded powers of the exponential base"
            )
        replacements[atom.symbol] = X / degree
    L = sp.expand(logarithmic.value.xreplace(replacements))
    lp = polynomial(L)
    if lp.degree() != 2 or lp.LC() <= 0 or lp.nth(0) != 0 or lp.nth(1) >= 0:
        raise UnsupportedCondition(
            "the logarithm factor must have a positive quadratic coefficient and two nonnegative levels"
        )
    level = -lp.nth(1) / lp.nth(2)
    if level.is_Rational is not True or not 0 < level <= 8 or level.q > 20:
        raise UnsupportedCondition(
            "a bounded positive rational second logarithm level is required"
        )
    return first.argument, shift, L, level


def analyze(formula):
    operator, e, logarithmic, atoms = read_product(formula)
    base = e.base
    argument, shift, L, level = logarithm_factor(logarithmic, atoms, base)
    z = e.stage.zeros[0]
    if z != 1 - shift or e.stage.solution != sp.Interval.open(-sp.oo, z):
        raise UnsupportedCondition(
            "the exponential zero must coincide with the zero logarithm level and change from positive to negative"
        )
    domain = sp.Interval.open(-shift, sp.oo)
    w = base**level - shift
    # base > 1 and level > 0 prove this order, including fourth-root endpoints.
    points = (-shift, z, w)
    signs = (1, 1, -1)
    ranges = (
        sp.Interval.open(-shift, z),
        sp.Interval.open(z, w),
        sp.Interval.open(w, sp.oo),
    )
    parts = [
        part
        for sign, part in zip(signs, ranges, strict=True)
        if accepts(sp.Integer(sign), operator)
    ]
    if operator.endswith("="):
        parts.extend((sp.FiniteSet(z), sp.FiniteSet(w)))
    solution = sp.Union(*parts)
    return ExponentialLogProduct(
        operator,
        base,
        argument,
        shift,
        e.exponents,
        L,
        comparison(L, ">="),
        domain,
        z,
        w,
        level,
        points,
        signs,
        solution,
    )
