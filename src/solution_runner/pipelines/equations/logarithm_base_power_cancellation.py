"""Cancel an exact positive base power without losing the original rational domain."""

import re
from dataclasses import dataclass, replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_factor_arguments import read_argument
from .logarithm_single_rationalization import analyze as single_logarithm
from .power_arithmetic import ScalarParser
from .rational_inequality import FLIPPED, OPERATORS
from .rational_inequality_parser import polynomial
from .rational_inequality_proof import RELATION
from .rational_inequality_roots import ordered, real_roots
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class BasePowerCancellation:
    base: sp.Expr
    argument: object
    bound: sp.Expr
    operator: str
    linear: sp.Expr
    sign: int
    logarithm: object

    @property
    def answer(self):
        return self.logarithm.answer


def reduced_factor(value):
    n, d = sp.fraction(sp.cancel(value))
    if d == 1:
        linear, sign = n, 1
    elif n.is_Rational is True and n > 0:
        linear, sign = sp.expand(d / n), -1
    else:
        raise UnsupportedCondition(
            "the complete reduced argument must be affine or its reciprocal"
        )
    p = polynomial(linear)
    if p.degree() != 1 or p.LC() <= 0:
        raise UnsupportedCondition(
            "the remaining logarithm argument must be increasing affine"
        )
    return linear, sign


def analyze(formula):
    pieces = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(pieces) != 3 or pieces[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one whole variable-base logarithm comparison is required"
        )
    arguments = []

    def reader(raw):
        argument = read_argument(raw)
        arguments.append(argument)
        return argument.value

    atoms, expression = read_equation(
        pieces[0] + "=0",
        extended=True,
        argument_reader=reader,
        argument_powers=True,
    )
    if len(atoms) != 1 or len(arguments) != 1 or atoms[0].root or atoms[0].denominator:
        raise UnsupportedCondition(
            "one complete rational-argument logarithm is required"
        )
    atom, argument = atoms[0], arguments[0]
    bound = ScalarParser(pieces[2]).parse()
    base = polynomial(atom.base)
    if (
        base.degree() != 1
        or base.LC() >= 0
        or bound.is_Integer is not True
        or abs(bound) > 10
        or expression != atom.symbol
    ):
        raise UnsupportedCondition(
            "one decreasing affine base and an unscaled bounded integer level are required"
        )
    B = atom.base
    linear, sign = reduced_factor(sp.cancel(argument.value / B**bound))
    operator = OPERATORS[pieces[1]]
    reduced_operator = operator if sign == 1 else FLIPPED[operator]
    reduced = single_logarithm(
        r"\log_{"
        + sp.latex(B)
        + "}("
        + sp.latex(linear)
        + ")"
        + RELATION[reduced_operator]
        + "0"
    )
    domain = comparison(B, ">").solution.intersect(argument.domain) - sp.FiniteSet(
        *real_roots(B - 1)
    )
    if reduced.domain - sp.FiniteSet(*argument.excluded) != domain:
        raise UnsupportedCondition(
            "cancelling the positive base power must preserve the complete original domain"
        )
    logarithm = replace(
        reduced,
        poles=ordered(set(reduced.poles) | set(argument.excluded)),
        domain=domain,
        solution=reduced.product.solution.intersect(domain),
    )
    return BasePowerCancellation(B, argument, bound, operator, linear, sign, logarithm)
