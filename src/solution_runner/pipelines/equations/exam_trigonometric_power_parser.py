"""Share power syntax while each method certifies its permitted exponents."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_arithmetic import power
from .logarithm_parser import Node


class PowerFactors:
    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            node = self._factor()
            return node if token == "+" else Node(-node.value, "", "negative", (node,))
        node = self._primary()
        if self.text[self.index : self.index + 1] != "^":
            return node
        exponent = self._exponent()
        if not exponent.value.free_symbols:
            value = power(node.value, exponent.value)
        else:
            value = self.variable_power(node.value, exponent.value)
        return Node(value, "", "power", (node, exponent))


class PositivePowerParser(PowerFactors, ExamAngleParser):
    def _nested(self, text):
        return type(self)(text, self.atoms, self.denominators, self.depth + 1).parse()

    def variable_power(self, base, exponent):
        if base.is_Pow and base.base.is_Rational:
            base, exponent = base.base, base.exp * exponent
        if (
            base.is_Rational is not True
            or not sp.Rational(1, 10000) <= base <= 10000
            or base == 1
            or exponent.free_symbols - set(self.atoms)
        ):
            raise UnsupportedCondition(
                "bounded positive rational bases and original trig exponents are required"
            )
        return sp.Pow(base, exponent, evaluate=False)
