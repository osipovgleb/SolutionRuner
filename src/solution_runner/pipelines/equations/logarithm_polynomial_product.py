"""Combine polynomial-weighted logarithms on their complete original domains."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_arithmetic import log_ratio
from .logarithm_factor_arguments import read_argument
from .logarithm_rationalization import answer
from .rational_inequality import OPERATORS
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison


def read_product(formula):
    parts = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one complete polynomial-logarithm inequality is required"
        )
    arguments = []

    def reader(raw):
        argument = read_argument(raw)
        arguments.append(argument)
        return argument.value

    atoms, expression = read_equation(
        parts[0] + "=" + parts[2],
        extended=True,
        argument_reader=reader,
        argument_powers=True,
    )
    symbols = tuple(atom.symbol for atom in atoms)
    if (
        not 2 <= len(atoms) <= 3
        or any(
            a.root
            or a.denominator
            or a.base.is_Rational is not True
            or not 1 < a.base <= 1000
            for a in atoms
        )
        or sp.Poly(expression, *symbols).total_degree() != 1
        or expression.subs(dict.fromkeys(symbols, 0)) != 0
    ):
        raise UnsupportedCondition(
            "a complete linear combination of two or three increasing constant-base logarithms is required"
        )
    coefficients = tuple(expression.coeff(atom.symbol) for atom in atoms)
    if any(polynomial(c).degree() > 2 for c in coefficients):
        raise UnsupportedCondition(
            "outer logarithm coefficients may be quadratic polynomials only"
        )
    return tuple(atoms), tuple(arguments), coefficients, OPERATORS[parts[1]]


@dataclass(frozen=True)
class PolynomialLogProduct:
    base: sp.Expr
    argument: sp.Expr
    atoms: tuple
    arguments: tuple
    coefficients: tuple
    degrees: tuple
    ratios: tuple
    unscaled: sp.Expr
    scale: sp.Expr
    polynomial: sp.Expr
    domain: object
    operator: str
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    atoms, arguments, coefficients, operator = read_product(formula)
    affine = next(
        (
            a.value
            for a in arguments
            if a.value.is_polynomial(X) and polynomial(a.value).degree() == 1
        ),
        None,
    )
    if affine is None:
        raise UnsupportedCondition(
            "one complete affine argument must fix the original positive domain"
        )
    base = min(atom.base for atom in atoms)
    degrees, ratios = [], []
    for atom in atoms:
        degree = next(
            (k for k in range(1, 9) if sp.cancel(atom.argument - affine**k) == 0), None
        )
        ratio = log_ratio(base, atom.base)
        if degree is None or ratio.is_Integer is not True or not 1 <= ratio <= 12:
            raise UnsupportedCondition(
                "every complete argument must be a bounded power of the affine argument with commensurate increasing bases"
            )
        degrees.append(degree)
        ratios.append(ratio)
    unscaled = sp.expand(
        sum(c * k / r for c, k, r in zip(coefficients, degrees, ratios, strict=True))
    )
    p = polynomial(unscaled)
    if (
        p.degree() != 2
        or any(c.is_Rational is not True for c in p.all_coeffs())
        or p.LC() <= 0
    ):
        raise UnsupportedCondition(
            "the combined complete coefficient must be a positive-leading rational quadratic"
        )
    scale = sp.ilcm(*(c.q for c in p.all_coeffs()))
    value = sp.expand(scale * unscaled)
    domain = sp.Intersection(*(arg.domain for arg in arguments))
    if domain.is_subset(comparison(affine, ">").solution) is not True:
        raise UnsupportedCondition(
            "the affine logarithm argument must be positive on the entire original domain"
        )
    stage = comparison(value * (affine - 1), operator)
    return PolynomialLogProduct(
        base,
        affine,
        atoms,
        arguments,
        coefficients,
        tuple(degrees),
        tuple(ratios),
        unscaled,
        scale,
        value,
        domain,
        operator,
        stage,
        stage.solution.intersect(domain),
    )
