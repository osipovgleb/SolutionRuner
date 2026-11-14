"""One variable-base logarithm, with shared product/quotient rationalization math."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .logarithm_rationalization import answer
from .rational_inequality import analyze as rational
from .rational_inequality_parser import polynomial
from .rational_inequality_proof import RELATION
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms, VariableLogarithmParser


@dataclass(frozen=True)
class SingleLogRationalization:
    G: sp.Expr
    A: sp.Expr
    bound: sp.Expr
    operator: str
    domains: tuple
    poles: tuple
    domain: object
    power: sp.Expr
    product: object
    quotient: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula.removesuffix("."),
        reader=lambda text: VariableLogarithmParser(text, atoms=atoms),
    )
    if (
        len(atoms.values) != 1
        or left.value != atoms.values[0].symbol
        or right.value.is_Integer is not True
        or not 0 <= right.value <= 2
    ):
        raise UnsupportedCondition(
            "one complete variable logarithm and a reviewed integer bound are required"
        )
    atom = atoms.values[0]
    G, A = atom.base, atom.argument
    if not 1 <= polynomial(G).degree() <= 2 or not 1 <= polynomial(A).degree() <= 2:
        raise UnsupportedCondition(
            "complete affine or quadratic polynomial base and argument are required"
        )
    return solve_parts(G, A, right.value, operator, denominators)


def solve_parts(G, A, bound, operator, denominators):
    poles = excluded_points((*denominators, G - 1))
    domains = (comparison(G, ">").solution, comparison(A, ">").solution)
    domain = sp.Intersection(*domains) - sp.FiniteSet(*poles)
    power = G**bound
    product = rational(sp.latex((G - 1) * (A - power)) + RELATION[operator] + "0")
    quotient = rational(
        r"\frac{"
        + sp.latex(A - power)
        + "}{"
        + sp.latex(G - 1)
        + "}"
        + RELATION[operator]
        + "0"
    )
    solution = product.solution.intersect(domain)
    if quotient.solution.intersect(domain) != solution:
        raise UnsupportedCondition(
            "both rationalizations must preserve the complete original domain"
        )
    return SingleLogRationalization(
        G,
        A,
        bound,
        operator,
        domains,
        poles,
        domain,
        power,
        product,
        quotient,
        solution,
    )
