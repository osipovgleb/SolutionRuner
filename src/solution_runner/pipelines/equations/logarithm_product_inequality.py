"""Compare three same-base logarithms while certifying the original argument domain."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .rational_inequality import OPERATORS, set_latex
from .rational_inequality import analyze as rational
from .rational_inequality_algebraic_methods import original_orientation
from .rational_inequality_parser import RationalParser, polynomial
from .rational_inequality_roots import ordered
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class ProductComparison:
    formula: str
    operator: str
    base: sp.Expr
    arguments: tuple
    domains: tuple
    displayed_indices: tuple
    domain: object
    display_domain: object
    stage: object
    solution: object
    full_stage: object = None
    argument_texts: tuple = ()
    argument_holes: tuple = ()

    @property
    def answer(self):
        return set_latex(self.solution)


def read_input(formula, method):
    if method not in ("product", "quotient"):
        raise UnsupportedCondition("unknown logarithm comparison method")
    raw_arguments = []

    def read_argument(text):
        raw_arguments.append(text)
        return RationalParser(text).parse().value

    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete logarithmic inequality is required")
    atoms, expression = read_equation(
        parts[0] + "=" + parts[2],
        extended=True,
        argument_reader=read_argument if method == "quotient" else None,
    )
    if len(atoms) != 3 or any(a.root or a.denominator for a in atoms):
        raise UnsupportedCondition(
            "three complete logarithms without outer roots or poles are required"
        )
    base = atoms[0].base
    if (
        base.is_Rational is not True
        or base <= 0
        or base == 1
        or any(a.base != base for a in atoms)
    ):
        raise UnsupportedCondition(
            "the three logarithms must have the same positive rational base different from one"
        )
    if sp.expand(expression - atoms[0].symbol + atoms[1].symbol + atoms[2].symbol) != 0:
        raise UnsupportedCondition(
            "one logarithm must be compared with the sum of two others"
        )
    arguments = tuple(a.argument for a in atoms)
    return OPERATORS[parts[1]], base, arguments, tuple(raw_arguments)


def transformed(arguments, base, operator, method):
    if method == "product":
        if any(polynomial(value).degree() not in (1, 2) for value in arguments):
            raise UnsupportedCondition(
                "the reviewed arguments must be affine or quadratic"
            )
    else:
        if polynomial(arguments[1]).degree() != 1:
            raise UnsupportedCondition(
                "the quotient method needs an affine positive middle argument"
            )
        for argument in arguments:
            n, d = sp.fraction(sp.cancel(argument))
            if polynomial(n).degree() > 2 or polynomial(d).degree() > 2:
                raise UnsupportedCondition(
                    "the quotient arguments must have bounded quadratic parts"
                )
    A, B, C = arguments
    difference = sp.expand((1 if base > 1 else -1) * (A - B * C))
    if method == "product" and polynomial(difference).degree() != 3:
        raise UnsupportedCondition(
            "the parent grouping requires a cubic argument difference"
        )
    stage = comparison(difference, operator)
    full_stage = None
    if method == "quotient":
        n, d = sp.fraction(sp.cancel(difference))
        if polynomial(n).degree() != 2 or polynomial(d).degree() > 2:
            raise UnsupportedCondition(
                "the quotient comparison must reduce to a quadratic rational fraction"
            )
        full_stage = comparison((1 if base > 1 else -1) * (A / B - C), operator)
    return stage, full_stage


def analyze(formula, *, method="product"):
    operator, base, arguments, raw_arguments = read_input(formula, method)
    stage, full_stage = transformed(arguments, base, operator, method)
    domains = (
        tuple(original_orientation(rational(text + r"\gt 0")) for text in raw_arguments)
        if method == "quotient"
        else tuple(comparison(argument, ">") for argument in arguments)
    )
    domain = sp.Intersection(*(d.solution for d in domains))
    if method == "product":
        implied = (base < 1 and operator in ("<", "<=")) or (
            base > 1 and operator in (">", ">=")
        )
        indices = (1, 2) if implied else (0, 1, 2)
    else:
        implied = (base > 1 and operator in ("<", "<=")) or (
            base < 1 and operator in (">", ">=")
        )
        indices = (0, 1) if implied else (0, 1, 2)
    display_domain = sp.Intersection(*(domains[i].solution for i in indices))
    solution = stage.solution.intersect(domain)
    if display_domain.intersect(stage.solution) != solution:
        indices = (0, 1, 2)
        display_domain = domain
    if full_stage is not None and full_stage.solution.intersect(domain) != solution:
        raise UnsupportedCondition(
            "removing the positive middle factor must preserve the full source solution"
        )
    holes = ordered({p for d in domains for p in d.holes})
    return ProductComparison(
        formula,
        operator,
        base,
        arguments,
        domains,
        indices,
        domain,
        display_domain,
        stage,
        solution,
        full_stage,
        tuple(raw_arguments),
        holes,
    )
