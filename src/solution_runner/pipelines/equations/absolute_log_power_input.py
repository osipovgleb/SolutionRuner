"""Read weighted whole powers with complete numeric-base logarithm exponents."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_input import AbsolutePowerReader
from .logarithm_parser import Node
from .logarithm_rationalization_input import complete_log
from .power_arithmetic import balanced
from .rational_inequality_parser import RationalParser


@dataclass(frozen=True)
class LogExponent:
    shift: sp.Expr
    base: sp.Expr
    argument: sp.Expr


class AbsoluteLogPowerReader(AbsolutePowerReader):
    def __init__(self, text, values, logarithms):
        text = re.sub(r"\\log_([2-9])(?=\s|\^|\()", r"\\log_{\1}", text)
        super().__init__(text, values)
        self.logarithms = logarithms

    def rational(self, text):
        return sp.cancel(RationalParser(text, self.denominators).parse().value)

    def base(self, index):
        if self.text[index : index + 1] != "(":
            return super().base(index)
        raw, end = balanced(self.text, index, "(", ")")
        base = Node(self.rational(raw), "", "scalar")
        if base.value.is_Rational is not True or base.value <= 0:
            raise UnsupportedCondition(
                "one whole positive numeric parenthesized base is required"
            )
        return base, end

    def exponent(self, raw):
        match = re.match(r"([0-8])\+", raw)
        shift = sp.Integer(match[1]) if match else sp.Integer(0)
        text = raw[match.end() :] if match else raw
        if text.startswith(r"\log_{"):
            _, end = balanced(text, 5)
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text[end:]):
                text = text[:end] + "(" + text[end:] + ")"
        atom, base, _ = complete_log(
            text,
            self.rational,
        )
        if len(self.logarithms) >= 3:
            raise UnsupportedCondition(
                "at most three complete logarithmic exponents are reviewed"
            )
        symbol = sp.Dummy("log_exponent", real=True)
        self.logarithms[symbol] = LogExponent(shift, base, atom.argument)
        return Node(symbol, "", "log_exponent")

    def term(self, index):
        match = re.match(r"([1-9]\d{0,5})(?:\\cdot|\\times|\*)", self.text[index:])
        coefficient = sp.Integer(match[1]) if match else sp.Integer(1)
        if match:
            index += match.end()
        power, index = self.power(index)
        return (coefficient, power), index

    def parse(self):
        first, index = self.term(0)
        if index == len(self.text):
            return Node(first[1].value, "", "weighted_power", first)
        if self.text[index : index + 1] != "+":
            raise UnsupportedCondition(
                "only two whole positive weighted power terms may be summed"
            )
        second, index = self.term(index + 1)
        if index != len(self.text):
            raise UnsupportedCondition(
                "the entire weighted power sum must be recognized"
            )
        return Node(
            first[1].value + second[1].value, "", "weighted_sum", (first, second)
        )
