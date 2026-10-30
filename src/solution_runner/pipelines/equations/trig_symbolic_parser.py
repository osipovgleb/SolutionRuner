"""Affine Greek arguments reuse the numeric trigonometric arithmetic grammar."""

import re
from dataclasses import dataclass
from functools import reduce
from math import gcd

import sympy as sp

from ..probability.common import UnsupportedCondition
from .power_arithmetic import ScalarParser, clean
from .trig_angles import PI, C, S, multiple_angle, reduce_polynomial
from .trig_parser import TrigonometricParser

A = sp.Symbol("a", real=True)


@dataclass(frozen=True)
class SymbolicAtom:
    function: str
    coefficient: int
    shift: sp.Rational
    variable: str
    text: str


class SymbolicTrigonometricParser(TrigonometricParser):
    def _nested(self, text):
        return SymbolicTrigonometricParser(
            text, self.atoms, self.denominators, self.depth + 1
        ).parse()

    def _angle(self):
        match = re.match(
            r"[+-]?(?:\d+)?\\(?:alpha|beta|gamma)", self.text[self.index :]
        )
        if match:
            self.index += match.end()
            return match.group()
        return super()._angle()

    def _atom(self, function, angle):
        variables = set(re.findall(r"\\(?:alpha|beta|gamma)", angle))
        if len(variables) != 1:
            raise UnsupportedCondition("one declared Greek angle is required")
        variable = variables.pop()
        expression = ScalarParser(
            clean(angle).replace(variable, "a").replace(r"\pi", "p"), {"a", "p"}
        ).parse()
        coefficient = sp.expand(expression).coeff(A)
        shift = sp.cancel((expression - coefficient * A) / PI)
        if (
            coefficient.is_Integer is not True
            or not -100 <= coefficient <= 100
            or shift.is_Rational is not True
            or (2 * shift).is_Integer is not True
            or abs(shift) > 1000
        ):
            raise UnsupportedCondition(
                "a bounded integer angle multiple and half-pi shift are required"
            )
        atom = SymbolicAtom(
            function,
            int(coefficient),
            shift,
            variable,
            chr(92) + function + "(" + angle + ")",
        )
        return sp.Symbol("T" + str(len(self.atoms)), real=True), atom


def compile_atoms(parser):
    atoms = list(parser.atoms.values())
    if not atoms or len({a.variable for a in atoms}) != 1:
        raise UnsupportedCondition("the expression must use one Greek angle")
    base = reduce(gcd, (abs(a.coefficient) for a in atoms))
    if not base:
        raise UnsupportedCondition("a variable angle is required")
    values = {}
    poles = []
    for symbol, atom in parser.atoms.items():
        k = atom.coefficient // base
        if abs(k) > 4:
            raise UnsupportedCondition(
                "the symbolic angle multiple exceeds the reviewed range"
            )
        h = int(2 * atom.shift)
        values[symbol] = multiple_angle(atom.function, k, h)
        if atom.function in ("tg", "ctg"):
            poles.append(
                multiple_angle("cos" if atom.function == "tg" else "sin", k, h)
            )
    denominators = poles + [d.xreplace(values) for d in parser.denominators]
    for denominator in denominators:
        if reduce_polynomial(denominator) == 0:
            raise UnsupportedCondition(
                "the original symbolic denominator vanishes identically"
            )
    return base, atoms[0].variable, values, denominators


def formula(expression, theta):
    return sp.latex(
        expression,
        symbol_names={S: r"(\sin(" + theta + "))", C: r"(\cos(" + theta + "))"},
    )
