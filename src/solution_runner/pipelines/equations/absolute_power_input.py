"""Read whole outer powers without evaluating variable exponents or losing poles."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_inequality_input import AbsoluteParser
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean
from .rational_inequality_parser import RationalParser


class AbsolutePowerReader:
    def __init__(self, text, values):
        self.text = clean(text)
        self.values = values
        self.denominators = []

    def power(self, index):
        start = index
        if self.text[index : index + 1] == "|":
            end = self.text.find("|", index + 1)
            if end < 0:
                raise UnsupportedCondition("a complete modulus base is required")
            base = AbsoluteParser(
                self.text[index : end + 1], self.denominators, values=self.values
            ).parse()
            index = end + 1
            # The reviewed parent has a stray punctuation dot between |P| and ^{E}.
            if self.text[index : index + 3] == ".^{":
                index += 1
        else:
            match = re.match(
                r"(?:[1-9]\d{0,5}|\\frac\{[1-9]\d{0,5}\}\{[1-9]\d{0,5}\})",
                self.text[index:],
            )
            if match is None:
                raise UnsupportedCondition(
                    "a bounded positive numeric or modulus base is required"
                )
            index += match.end()
            base = RationalParser(self.text[start:index], self.denominators).parse()
        if self.text[index : index + 2] != "^{":
            raise UnsupportedCondition("one whole explicitly braced power is required")
        raw, index = balanced(self.text, index + 1)
        exponent = AbsoluteParser(raw, self.denominators, values=self.values).parse()
        return Node(
            sp.Dummy("power", positive=True), "", "exponential", (base, exponent)
        ), index

    def parse(self):
        if "^" not in self.text:
            return RationalParser(self.text, self.denominators).parse()
        first, index = self.power(0)
        if index == len(self.text):
            return first
        if self.text[index : index + 1] != "+":
            raise UnsupportedCondition(
                "only one power or a sum of two complete powers is reviewed"
            )
        second, index = self.power(index + 1)
        if index != len(self.text):
            raise UnsupportedCondition("the complete two-power sum must be recognized")
        return Node(first.value + second.value, "", "add", (first, second))
