"""Prove the logarithm product/quotient domain before comparing factored powers."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .logarithm_factored_power_input import FactoredLogParser
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms


@dataclass(frozen=True)
class FactoredLogPower:
    base: sp.Expr
    log_base: sp.Expr
    high_shift: int
    middle_shift: int
    left_constant: sp.Expr
    right_constant: sp.Expr
    poles: tuple
    stage: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def coordinates(powers):
    shifts = {}
    bases = set()
    for symbol, (base, exponent) in powers.items():
        shift = sp.expand(exponent + X**2)
        if (
            base.is_Integer is not True
            or not 2 <= base <= 10
            or shift.is_Integer is not True
            or not 0 <= shift <= 32
            or shift in shifts
        ):
            raise UnsupportedCondition(
                "each complete exponent must be minus x squared plus one bounded distinct integer shift"
            )
        shifts[int(shift)] = symbol
        bases.add(base)
    order = sorted(shifts)
    if (
        len(bases) != 1
        or len(order) != 3
        or order[0] != 0
        or not 0 < order[1] < order[2]
    ):
        raise UnsupportedCondition(
            "three same-base powers with shifts zero, middle and high are required"
        )
    return (
        bases.pop(),
        order[1],
        order[2],
        shifts[0],
        shifts[order[1]],
        shifts[order[2]],
    )


def original_poles(denominators, powers, high_symbol):
    ordinary = []
    for value in denominators:
        if value.free_symbols & set(powers):
            ratio = sp.cancel(value / (high_symbol - 1))
            if ratio.is_Rational is not True or ratio == 0:
                raise UnsupportedCondition(
                    "a typed original denominator must be the reviewed high-power difference, proved nonzero on the source domain"
                )
        else:
            ordinary.append(value)
    return excluded_points(ordinary)


def analyze(formula):
    atoms = Atoms()
    powers = {}
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: FactoredLogParser(text, atoms=atoms, powers=powers)
    )
    if (
        operator != ">"
        or left.kind != "add"
        or right.kind != "logarithm"
        or len(atoms.values) != 3
        or any(n.kind != "logarithm" for n in left.children)
    ):
        raise UnsupportedCondition(
            "the complete input must be two added logarithms compared strictly with a third"
        )
    first = atoms.values[0]
    if tuple(n.value for n in (*left.children, right)) != tuple(
        a.symbol for a in atoms.values
    ):
        raise UnsupportedCondition(
            "all three logarithms must remain complete unweighted terms"
        )
    B = sp.cancel(first.base)
    if (
        B.is_Rational is not True
        or not 1 < B <= 1000
        or any(sp.cancel(a.base - B) != 0 for a in atoms.values)
    ):
        raise UnsupportedCondition(
            "all three logarithms need the same bounded increasing numeric base"
        )
    A, M, N, t, u, v = coordinates(powers)
    F, G, H = (a.argument for a in atoms.values)
    c = sp.expand(F).subs({s: 0 for s in powers})
    if (
        c.is_Rational is not True
        or not 1 < c <= 100
        or sp.expand(F - (t - c) * (v - 1)) != 0
        or sp.cancel(G - (t - c) / (v - 1)) != 0
    ):
        raise UnsupportedCondition(
            "both complete left arguments must be the parent product and quotient of the same two differences"
        )
    if H.free_symbols - {u} or not H.is_polynomial(u):
        raise UnsupportedCondition(
            "the right argument must be the whole square of one middle-power difference"
        )
    p = sp.Poly(H, u)
    d = -p.nth(1) / 2
    if (
        p.degree() != 2
        or p.LC() != 1
        or d.is_Rational is not True
        or not 1 <= d <= c
        or sp.expand(H - (u - d) ** 2) != 0
    ):
        raise UnsupportedCondition(
            "the squared right difference must have a matching positive bounded constant"
        )
    poles = original_poles(denominators, powers, v)
    stage = comparison(X**2 - N, ">")
    return FactoredLogPower(
        A, B, N, M, c, d, poles, stage, stage.solution - sp.FiniteSet(*poles)
    )
