"""Reuse the exact scalar grammar, retaining every original denominator."""

import re

import sympy as sp

from ..equations.power_arithmetic import ScalarParser, balanced
from ..probability.common import UnsupportedCondition


def canonical_formula(raw, aliases):
    def substitute(match):
        token = match[0]
        if token in aliases:
            return aliases[token]
        if token in [r"\frac", r"\cdot", r"\left", r"\right", r"\sqrt"]:
            return token
        raise UnsupportedCondition("an undeclared physical formula variable remains")

    canonical = re.sub(
        r"\\[a-zA-Z]+(?:_[a-z])?|[A-Za-z](?:_(?:\d|[a-z]+))?", substitute, raw
    )
    canonical = re.sub(r"([})])\s*(?=\()", r"\1\\cdot ", canonical)
    return re.sub(r"([xabde])\s*(?=\\frac|\()", r"\1\\cdot ", canonical)


class RationalFormulaParser(ScalarParser):
    def __init__(self, text, variables, denominators=None, depth=0):
        super().__init__(text, variables)
        self.denominators = [] if denominators is None else denominators
        self.depth = depth
        if depth > 20:
            raise UnsupportedCondition(
                "rational formula nesting exceeds the supported range"
            )

    def nested(self, text):
        return RationalFormulaParser(
            text, self.variables, self.denominators, self.depth + 1
        ).parse()

    def _factor(self):
        value = self._operand()
        if self.text[self.index : self.index + 1] == "^":
            self.index += 1
            if self.text[self.index : self.index + 1] == "{":
                raw, self.index = balanced(self.text, self.index)
            else:
                raw = self.text[self.index : self.index + 1]
                self.index += 1
            if not re.fullmatch(r"[1-6]", raw):
                raise UnsupportedCondition(
                    "a positive integer power at most six is required"
                )
            value **= int(raw)
        return value

    def _operand(self):
        if self.text[self.index : self.index + 1] == "|":
            end = self.text.find("|", self.index + 1)
            if end < 0:
                raise UnsupportedCondition("an absolute value must have two delimiters")
            raw = self.text[self.index + 1 : end]
            self.index = end + 1
            return sp.Abs(self.nested(raw))
        if self.text[self.index : self.index + 1] == "(":
            text, self.index = balanced(self.text, self.index, "(", ")")
            return self.nested(text)
        if self.text.startswith(r"\frac", self.index):
            self.index += 5
            numerator, self.index = balanced(self.text, self.index)
            denominator, self.index = balanced(self.text, self.index)
            numerator, denominator = self.nested(numerator), self.nested(denominator)
            if denominator == 0:
                raise UnsupportedCondition("an original formula denominator is zero")
            self.denominators.append(denominator)
            return numerator / denominator
        if self.text.startswith(r"\sqrt", self.index):
            raise UnsupportedCondition("the physical formula must be rational")
        return super()._factor()


class SquareRootFormulaParser(RationalFormulaParser):
    def __init__(self, text, variables, denominators=None, depth=0, roots=None):
        super().__init__(text, variables, denominators, depth)
        self.roots = [] if roots is None else roots

    def nested(self, text):
        return SquareRootFormulaParser(
            text, self.variables, self.denominators, self.depth + 1, self.roots
        ).parse()

    def _operand(self):
        if not self.text.startswith(r"\sqrt", self.index):
            return super()._operand()
        self.index += 5
        raw, self.index = balanced(self.text, self.index)
        radicand = self.nested(raw)
        self.roots.append(radicand)
        return sp.sqrt(radicand)
