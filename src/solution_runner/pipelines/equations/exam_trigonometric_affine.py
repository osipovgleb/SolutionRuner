"""Separate bounded rational algebraic roots from a unit sine/cosine factor."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import X
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import ScalarParser, clean


@dataclass(frozen=True)
class AffineFactor:
    source: sp.Expr
    algebraic: sp.Expr
    roots: tuple
    algebraic_first: bool = False

    @property
    def quadratic(self):
        return sp.degree(self.algebraic, X) == 2


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
    if not raw.is_polynomial(X, S, C) or sp.Poly(raw, X, S, C).total_degree() > 3:
        raise UnsupportedCondition(
            "one bounded algebraic and one affine trigonometric factor are required"
        )
    _, factors = sp.factor_list(raw, X, S, C, extension=True)
    algebraic = [(f, power) for f, power in factors if f.free_symbols == {X}]
    trig = [
        f
        for f, power in factors
        if f.free_symbols in ({S}, {C})
        and power == 1
        and sp.Poly(f, *f.free_symbols).degree() == 1
    ]
    if len(trig) != 1 or len(algebraic) + 1 != len(factors) or not algebraic:
        raise UnsupportedCondition(
            "the mixed equation must separate into algebraic factors and one affine trig factor"
        )
    polynomial = sp.prod(f**power for f, power in algebraic)
    degree = sp.degree(polynomial, X)
    if degree not in (1, 2) or any(
        v.is_Rational is not True for v in sp.Poly(polynomial, X).all_coeffs()
    ):
        raise UnsupportedCondition(
            "a rational algebraic factor of degree one or two is required"
        )
    if degree == 2:
        polynomial = primitive(sp.expand(polynomial), (X,))
        _, root_factors = sp.factor_list(polynomial, X)
    else:
        root_factors = algebraic
    if any(sp.degree(f, X) != 1 for f, _ in root_factors):
        raise UnsupportedCondition("all isolated roots must be rational linear factors")
    roots = tuple(
        dict.fromkeys(sp.cancel(-f.subs(X, 0) / f.coeff(X)) for f, _ in root_factors)
    )
    if any(root.is_Rational is not True or abs(root) > 1000 for root in roots):
        raise UnsupportedCondition("bounded rational isolated roots are required")
    return Equation(trig[0], (), sp.S.One, affine=AffineFactor(raw, polynomial, roots))


def prepare(equation, parent_html):
    if equation.affine is None or not equation.affine.quadratic:
        return equation
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = clean(node["data-inline-latex"]).replace("&", "")
        for part in re.split(r"\\(?:iff|Leftrightarrow)|\\\\", text):
            match = re.search(r"(\\(?:sin|cos))?x=([^=]*)", part)
            if match is None:
                continue
            try:
                value = ScalarParser(match[2].rstrip(".,")).parse()
            except UnsupportedCondition:
                continue
            if value.is_real is True and not value.free_symbols:
                return replace(
                    equation,
                    affine=replace(equation.affine, algebraic_first=match[1] is None),
                )
    raise UnsupportedCondition(
        "the parent must show the order of algebraic and trigonometric branches"
    )


def reviewed(formula, scale, translation):
    equation = compile_affine(formula)
    if equation is not None and (translation or scale != 1):
        raise UnsupportedCondition(
            "mixed affine equations require the original unit angle"
        )
    return equation
