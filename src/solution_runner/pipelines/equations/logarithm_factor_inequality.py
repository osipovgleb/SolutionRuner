"""Combine exact factor logarithms on their full original argument domains."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_arithmetic import log_ratio, power
from .logarithm_factor_arguments import read_argument
from .rational_inequality import FLIPPED, OPERATORS, set_latex
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class FactorComparison:
    base: sp.Expr
    atoms: tuple
    arguments: tuple
    coefficients: tuple
    weights: tuple
    constant: sp.Expr
    scalar: sp.Expr
    factors: tuple
    multiplier: sp.Expr
    reduced: sp.Expr
    threshold_squared: sp.Expr
    operator: str
    reduced_operator: str
    domain: object
    stage: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def read_input(formula):
    formula = re.sub(r"\\lg(?![a-zA-Z])", lambda _: r"\log_{10}", formula)
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one complete factor-logarithm inequality is required"
        )
    arguments = []

    def reader(text):
        argument = read_argument(text)
        arguments.append(argument)
        return argument.value

    atoms, expression = read_equation(
        parts[0] + "=" + parts[2],
        extended=True,
        argument_reader=reader,
        argument_powers=True,
    )
    symbols = tuple(a.symbol for a in atoms)
    if (
        not 2 <= len(atoms) <= 3
        or any(a.root or a.denominator for a in atoms)
        or expression.free_symbols - set(symbols)
        or not expression.is_polynomial(*symbols)
    ):
        raise UnsupportedCondition(
            "two or three complete logarithms and no external variables or poles are required"
        )
    if sp.Poly(expression, *symbols).total_degree() != 1:
        raise UnsupportedCondition("a linear combination of logarithms is required")
    base = atoms[0].base
    if any(
        a.base.is_Rational is not True or max(a.base.p, a.base.q) > 1000 for a in atoms
    ):
        raise UnsupportedCondition("bounded positive rational bases are required")
    coefficients = tuple(expression.coeff(a.symbol) for a in atoms)
    constant = expression.subs(dict.fromkeys(symbols, 0))
    if any(c.is_Rational is not True or abs(c) > 20 for c in (*coefficients, constant)):
        raise UnsupportedCondition(
            "bounded rational logarithm coefficients are required"
        )
    return base, atoms, tuple(arguments), coefficients, constant, OPERATORS[parts[1]]


def collect_factors(base, atoms, arguments, coefficients):
    weights = []
    factors = {}
    scalar = sp.Integer(1)
    for atom, arg, coefficient in zip(atoms, arguments, coefficients, strict=True):
        ratio = log_ratio(base, atom.base)
        if ratio.is_Rational is not True or ratio == 0:
            raise UnsupportedCondition(
                "the complete logarithm bases must be commensurate"
            )
        weight = coefficient / ratio
        if max(abs(weight.p), weight.q) > 40:
            raise UnsupportedCondition(
                "the base conversion coefficient exceeds the reviewed range"
            )
        weights.append(weight)
        scalar *= power(abs(arg.coefficient), weight)
        for factor, degree in arg.factors:
            factors[factor] = factors.get(factor, 0) + weight * degree
    factors = {f: k for f, k in factors.items() if k}
    return tuple(weights), factors, scalar


def primitive(factors):
    if not factors:
        raise UnsupportedCondition("a nonconstant residual logarithm is required")
    multiplier = abs(sp.gcd_list(list(factors.values())))
    if all(k < 0 for k in factors.values()):
        multiplier = -multiplier
    exponents = {f: sp.cancel(k / multiplier) for f, k in factors.items()}
    if any(k.is_Integer is not True for k in exponents.values()) or any(
        sum(
            sp.degree(f, X) * abs(k)
            for f, k in exponents.items()
            if (k > 0) == positive
        )
        > 4
        for positive in (True, False)
    ):
        raise UnsupportedCondition(
            "the primitive residual rational function exceeds degree four"
        )
    reduced = sp.cancel(sp.prod(f**k for f, k in exponents.items()))
    return multiplier, reduced


def analyze(formula):
    base, atoms, arguments, coefficients, constant, operator = read_input(formula)
    weights, factors, scalar = collect_factors(base, atoms, arguments, coefficients)
    multiplier, reduced = primitive(factors)
    threshold_squared = sp.simplify(
        power(base, -2 * constant / multiplier) * power(scalar, -2 / multiplier)
    )
    if threshold_squared.is_Rational is not True or threshold_squared <= 0:
        raise UnsupportedCondition(
            "one exact positive rational squared threshold is required"
        )
    reduced_operator = operator
    if multiplier < 0:
        reduced_operator = FLIPPED[reduced_operator]
    if base < 1:
        reduced_operator = FLIPPED[reduced_operator]
    domain = sp.Intersection(*(arg.domain for arg in arguments))
    stage = comparison(reduced**2 - threshold_squared, reduced_operator)
    return FactorComparison(
        base,
        atoms,
        tuple(arguments),
        coefficients,
        tuple(weights),
        constant,
        scalar,
        tuple(sorted(factors.items(), key=lambda v: sp.default_sort_key(v[0]))),
        multiplier,
        reduced,
        threshold_squared,
        operator,
        reduced_operator,
        domain,
        stage,
        stage.solution.intersect(domain),
    )
