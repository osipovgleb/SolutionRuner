"""Separate a real affine factor from a unit sine/cosine equation."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import clean


@dataclass(frozen=True)
class AffineFactor:
    source: sp.Expr
    algebraic: sp.Expr
    roots: tuple


class AffineParser(ExamAngleParser):
    implicit_prefixes = ExamAngleParser.implicit_prefixes + (r"\alpha",)

    def __init__(self, *args, seen=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen = [] if seen is None else seen

    def _nested(self, text):
        return AffineParser(
            text, self.atoms, self.denominators, self.depth + 1, seen=self.seen
        ).parse()

    def _primary(self):
        if self.text.startswith(r"\alpha", self.index):
            self.index += len(r"\alpha")
            self.seen.append(X)
            return Node(X, "x", "variable")
        return super()._primary()


def parse(formula):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        return None
    atoms, denominators, seen, values = {}, [], [], []
    try:
        for side in text.split("="):
            parser = AffineParser(
                side.replace("x", r"\alpha"), atoms, denominators, seen=seen
            )
            values.append(parser.parse().value)
    except UnsupportedCondition:
        if seen:
            raise
        return None
    if not seen:
        return None
    if any(d.free_symbols for d in denominators) or any(
        a.function not in ("sin", "cos") or a.coefficient != 1 or a.shift != 0
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "an affine factor allows only denominator-free unit sine and cosine"
        )
    compiled = {
        symbol: S if atom.function == "sin" else C for symbol, atom in atoms.items()
    }
    return sp.expand((values[0] - values[1]).xreplace(compiled))


def compile_affine(formula):
    raw = parse(formula)
    if raw is None:
        return None
    if not raw.is_polynomial(X, S, C) or sp.Poly(raw, X, S, C).total_degree() > 2:
        raise UnsupportedCondition(
            "one affine algebraic and one affine trigonometric factor are required"
        )
    _, factors = sp.factor_list(raw, X, S, C, extension=True)
    algebraic = [
        f
        for f, power in factors
        if f.free_symbols == {X} and power == 1 and sp.degree(f, X) == 1
    ]
    trig = [
        f
        for f, power in factors
        if f.free_symbols in ({S}, {C})
        and power == 1
        and sp.Poly(f, *f.free_symbols).degree() == 1
    ]
    if len(factors) != 2 or len(algebraic) != 1 or len(trig) != 1:
        raise UnsupportedCondition(
            "the mixed equation must separate into exactly two affine factors"
        )
    root = sp.cancel(-algebraic[0].subs(X, 0) / algebraic[0].coeff(X))
    if root.is_Rational is not True or abs(root) > 1000:
        raise UnsupportedCondition("a bounded rational isolated root is required")
    return Equation(
        trig[0], (), sp.S.One, affine=AffineFactor(raw, algebraic[0], (root,))
    )
