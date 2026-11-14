"""Certify a shared equality case for a positive power and a bounded logarithm."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_inequality import rational_polynomial
from .absolute_power_input import AbsolutePowerReader
from .exam_logarithmic_input import logarithm
from .exponential_inequality_common_base import read_terms
from .logarithm_parser import Node
from .rational_inequality import set_latex
from .rational_inequality_parser import RationalParser
from .rational_substitution_preimages import comparison, excluded_points


class BoundProductReader(AbsolutePowerReader):
    def __init__(self, text, values, atoms):
        super().__init__(text, values)
        self.atoms = atoms

    def parse(self):
        if "^" not in self.text:
            return RationalParser(self.text, self.denominators).parse()
        power, index = self.power(0)
        token = next(
            (s for s in (r"\cdot", r"\times", "*") if self.text.startswith(s, index)),
            None,
        )
        if token is None or not self.text.startswith(r"\log_", index + len(token)):
            raise UnsupportedCondition(
                "one whole power times one numeric logarithm is required"
            )
        atom, degree, end = logarithm(
            self.text,
            index + len(token),
            sp.Dummy("logarithm", real=True),
            argument_reader=lambda raw: (
                RationalParser(raw, self.denominators).parse().value
            ),
        )
        if end != len(self.text) or degree != 1 or atom.root:
            raise UnsupportedCondition(
                "the whole logarithm factor must have no outer square or root"
            )
        self.atoms.append(atom)
        return Node(
            power.value * atom.symbol,
            "",
            "multiply",
            (power, Node(atom.symbol, "", "logarithm")),
        )


@dataclass(frozen=True)
class ExponentialLogBound:
    base: sp.Expr
    log_base: sp.Expr
    argument: sp.Expr
    absolute_argument: sp.Expr
    center: sp.Expr
    poles: tuple
    domain: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def analyze(formula):
    values, atoms = {}, []
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: BoundProductReader(text, values, atoms)
    )
    if (
        left.kind != "multiply"
        or right.value != 1
        or operator != ">="
        or len(values) != 1
        or len(atoms) != 1
    ):
        raise UnsupportedCondition(
            "the parent compares one complete bounded product with one"
        )
    symbol, absolute_argument = next(iter(values.items()))
    base, exponent = (n.value for n in left.children[0].children)
    (atom,) = atoms
    for b in (base, atom.base):
        if b.is_Rational is not True or not 1 < b <= 10**6 or b.q > 10**6:
            raise UnsupportedCondition(
                "both numeric bases must be bounded increasing bases"
            )
    if exponent != -symbol:
        raise UnsupportedCondition("the whole exponent must be the negative modulus")
    p = rational_polynomial(absolute_argument, 1)
    rational_polynomial(atom.argument, 2)
    if sp.expand(atom.argument - atom.base + absolute_argument**2) != 0:
        raise UnsupportedCondition(
            "the entire logarithm argument must be its base minus the modulus argument squared"
        )
    poles = excluded_points(denominators)
    domain = comparison(atom.argument, ">", denominators=denominators).solution
    center = -p.nth(0) / p.nth(1)
    solution = comparison(absolute_argument, "=").solution.intersect(domain)
    return ExponentialLogBound(
        base,
        atom.base,
        atom.argument,
        absolute_argument,
        center,
        poles,
        domain,
        solution,
    )
