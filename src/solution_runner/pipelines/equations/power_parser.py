"""The multiplicative grammar shared by positive-base power expressions."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .power_arithmetic import (
    Exponent,
    ScalarParser,
    balanced,
    clean,
    combine,
    factor_base,
    raise_power,
)


class PowerParser:
    def __init__(self, text, variables=(), depth=0):
        self.text = clean(text)
        self.index = 0
        self.variables = variables
        self.depth = depth
        if depth > 20:
            raise UnsupportedCondition(
                "power expression nesting exceeds the supported range"
            )

    def parse(self):
        value = self._implicit()
        while self.index < len(self.text):
            sign = 1
            for operator in (r"\cdot", r"\times", r"\colon", r"\div", "*", "/"):
                if self.text.startswith(operator, self.index):
                    self.index += len(operator)
                    sign = -1 if operator in (r"\colon", r"\div", "/") else 1
                    break
            else:
                raise UnsupportedCondition(
                    "an explicit power product or quotient operator is required"
                )
            value = combine(value, self._implicit(), sign)
        return value

    def _implicit(self):
        value = self._factor()
        while self.index < len(self.text) and (
            self.text[self.index] in self.variables
            or self.text[self.index] == "("
            or self.text.startswith(r"\sqrt", self.index)
        ):
            value = combine(value, self._factor())
        return value

    def _nested(self, text):
        return PowerParser(text, self.variables, self.depth + 1).parse()

    def _factor(self):
        value = self._primary()
        if self.text[self.index : self.index + 1] == "^":
            self.index += 1
            if self.text[self.index : self.index + 1] == "{":
                exponent, self.index = balanced(self.text, self.index)
            else:
                match = re.match(r"[+-]?\d", self.text[self.index :])
                if match is None:
                    raise UnsupportedCondition(
                        "an explicit scalar exponent is required"
                    )
                exponent = match.group()
                self.index += match.end()
            parsed = ScalarParser(exponent, self.variables).parse()
            value = raise_power(value, Exponent(parsed, exponent.replace(".", "{,}")))
        return value

    def _primary(self):
        token = self.text[self.index : self.index + 1]
        if token == "(":
            text, self.index = balanced(self.text, self.index, "(", ")")
            return self._nested(text)
        if self.text.startswith(r"\frac", self.index):
            self.index += 5
            a, self.index = balanced(self.text, self.index)
            b, self.index = balanced(self.text, self.index)
            return combine(self._nested(a), self._nested(b), -1)
        if self.text.startswith(r"\sqrt", self.index):
            self.index += 5
            degree = 2
            if self.text[self.index : self.index + 1] == "[":
                text, self.index = balanced(self.text, self.index, "[", "]")
                if not re.fullmatch(r"\d{1,3}", text) or not 2 <= int(text) <= 100:
                    raise UnsupportedCondition(
                        "the root index must lie between 2 and 100"
                    )
                degree = int(text)
            radicand, self.index = balanced(self.text, self.index)
            return raise_power(
                self._nested(radicand),
                Exponent(sp.Rational(1, degree), rf"\frac{{1}}{{{degree}}}"),
            )
        if token in self.variables and token:
            self.index += 1
            return {token: [Exponent(sp.Integer(1), "1")]}
        match = re.match(r"\d+(?:\.\d+)?", self.text[self.index :])
        if match is None:
            raise UnsupportedCondition("unsupported positive power base")
        self.index += match.end()
        return factor_base(match.group())
