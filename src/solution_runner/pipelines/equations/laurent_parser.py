"""Read integer-power sums, monomial products and monomial denominators."""

import re
from fractions import Fraction

from ..probability.common import UnsupportedCondition
from . import laurent_arithmetic as arithmetic
from .power_arithmetic import ScalarParser, balanced, clean


class LaurentParser:
    def __init__(self, text, trace=None, nonzero=None, depth=0):
        self.text = clean(text)
        self.index = 0
        self.depth = depth
        self.trace = [] if trace is None else trace
        self.nonzero = set() if nonzero is None else nonzero
        if depth > 20:
            raise UnsupportedCondition(
                "Laurent expression nesting exceeds the supported range"
            )

    def parse(self):
        value = self._sum()
        if self.index != len(self.text):
            raise UnsupportedCondition("unsupported complete Laurent expression")
        return value

    def _nested(self, text):
        return LaurentParser(text, self.trace, self.nonzero, self.depth + 1).parse()

    def _sum(self):
        value = self._product()
        while self.text[self.index : self.index + 1] in ("+", "-"):
            operator = self.text[self.index]
            self.index += 1
            other = self._product()
            result = arithmetic.add(value, other, 1 if operator == "+" else -1)
            self.trace.append(
                arithmetic.latex(value)
                + operator
                + "("
                + arithmetic.latex(other)
                + ")="
                + arithmetic.latex(result)
            )
            value = result
        return value

    def _product(self):
        value = self._implicit()
        while self.index < len(self.text):
            for operator in (r"\cdot", r"\times", r"\colon", r"\div", "*", "/"):
                if self.text.startswith(operator, self.index):
                    self.index += len(operator)
                    break
            else:
                break
            other = self._implicit()
            quotient = operator in (r"\colon", r"\div", "/")
            result = (
                arithmetic.divide(value, other, self.nonzero)
                if quotient
                else arithmetic.multiply(value, other)
            )
            symbol = r"\colon " if quotient else r"\cdot "
            self.trace.append(
                "("
                + arithmetic.latex(value)
                + ")"
                + symbol
                + "("
                + arithmetic.latex(other)
                + ")="
                + arithmetic.latex(result)
            )
            value = result
        return value

    def _implicit(self):
        value = self._factor()
        while self.index < len(self.text) and (
            self.text[self.index].islower()
            or self.text[self.index] == "("
            or self.text.startswith(r"\sqrt", self.index)
        ):
            if self.text[self.index] == "(" and self.text[self.index - 1].islower():
                raise UnsupportedCondition(
                    "function notation is outside the Laurent grammar"
                )
            value = arithmetic.multiply(value, self._factor())
        return value

    def _factor(self):
        start = self.index
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            value = self._factor()
            return value if token == "+" else {k: -v for k, v in value.items()}
        value = self._primary()
        if self.text[self.index : self.index + 1] == "^":
            self.index += 1
            if self.text[self.index : self.index + 1] == "{":
                raw, self.index = balanced(self.text, self.index)
            else:
                match = re.match(r"[+-]?\d", self.text[self.index :])
                if match is None:
                    raise UnsupportedCondition(
                        "an explicit integer Laurent exponent is required"
                    )
                raw = match.group()
                self.index += match.end()
            exponent = ScalarParser(raw).parse()
            if exponent.is_Integer is not True or abs(exponent) > 1000:
                raise UnsupportedCondition(
                    "the Laurent exponent must be a bounded integer"
                )
            value = arithmetic.power(value, int(exponent), self.nonzero)
            if token == "(" or token.isdigit():
                self.trace.append(
                    self.text[start : self.index] + "=" + arithmetic.latex(value)
                )
        return value

    def _primary(self):
        token = self.text[self.index : self.index + 1]
        if token == "(":
            raw, self.index = balanced(self.text, self.index, "(", ")")
            return self._nested(raw)
        if self.text.startswith(r"\frac", self.index):
            self.index += 5
            a, self.index = balanced(self.text, self.index)
            b, self.index = balanced(self.text, self.index)
            numerator, denominator = self._nested(a), self._nested(b)
            result = arithmetic.divide(numerator, denominator, self.nonzero)
            self.trace.append(
                r"\frac{"
                + arithmetic.latex(numerator)
                + "}{"
                + arithmetic.latex(denominator)
                + "}="
                + arithmetic.latex(result)
            )
            return result
        if re.fullmatch("[a-z]", token):
            self.index += 1
            return {((token, 1),): Fraction(1)}
        match = re.match(r"\d+(?:\.\d+)?", self.text[self.index :])
        if match is None:
            raise UnsupportedCondition("unsupported Laurent expression operand")
        self.index += match.end()
        number = Fraction(match.group())
        if max(abs(number.numerator), number.denominator) > 10**9:
            raise UnsupportedCondition(
                "the Laurent coefficient exceeds the supported exact range"
            )
        return {(): number} if number else {}
