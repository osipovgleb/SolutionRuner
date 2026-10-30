"""Exact scalar exponents and prime-power bookkeeping, without expression eval."""

import re
from dataclasses import dataclass
from fractions import Fraction

import sympy as sp

from ..probability.common import UnsupportedCondition


def clean(text):
    if len(text) > 3000 or re.search(r"\d\s+\d", text):
        raise UnsupportedCondition("oversized or ambiguously spaced power expression")
    return "".join(
        text.replace(r"\left", "")
        .replace(r"\right", "")
        .replace("{,}", ".")
        .replace(",", ".")
        .replace("−", "-")
        .replace("–", "-")
        .split()
    )


def balanced(text, index, left="{", right="}"):
    if text[index : index + 1] != left:
        raise UnsupportedCondition("a braced power operand is required")
    start = index + 1
    depth = 1
    index = start
    while index < len(text) and depth:
        if text[index] == left:
            depth += 1
        elif text[index] == right:
            depth -= 1
        if depth > 20:
            raise UnsupportedCondition(
                "power expression nesting exceeds the supported range"
            )
        index += 1
    if depth:
        raise UnsupportedCondition("unclosed power expression operand")
    return text[start : index - 1], index


def rational(text):
    value = Fraction(text)
    if max(abs(value.numerator), value.denominator) > 10**9:
        raise UnsupportedCondition("power scalar exceeds the supported exact range")
    return sp.Rational(value.numerator, value.denominator)


class ScalarParser:
    """Read rational numbers and sums/products of square roots in an exponent."""

    def __init__(self, text):
        self.text = clean(text)
        self.index = 0
        if len(self.text) > 500:
            raise UnsupportedCondition("the scalar exponent is too long")

    def parse(self):
        value = self._sum()
        if self.index != len(self.text):
            raise UnsupportedCondition("unsupported complete scalar exponent")
        return sp.simplify(value)

    def _sum(self):
        value = self._product()
        while self.text[self.index : self.index + 1] in ("+", "-"):
            sign = self.text[self.index]
            self.index += 1
            other = self._product()
            value = value + other if sign == "+" else value - other
        return value

    def _product(self):
        value = self._factor()
        while self.index < len(self.text):
            if self.text.startswith(r"\cdot", self.index):
                self.index += 5
            elif self.text.startswith(r"\sqrt", self.index):
                pass
            else:
                break
            value *= self._factor()
        return value

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            return self._factor() * (1 if token == "+" else -1)
        if token == "(":
            text, self.index = balanced(self.text, self.index, "(", ")")
            return ScalarParser(text).parse()
        if self.text.startswith(r"\frac", self.index):
            self.index += 5
            a, self.index = balanced(self.text, self.index)
            b, self.index = balanced(self.text, self.index)
            denominator = ScalarParser(b).parse()
            if denominator == 0:
                raise UnsupportedCondition("division by zero in a scalar exponent")
            return ScalarParser(a).parse() / denominator
        if self.text.startswith(r"\sqrt", self.index):
            self.index += 5
            text, self.index = balanced(self.text, self.index)
            if not re.fullmatch(r"\d{1,6}", text):
                raise UnsupportedCondition(
                    "the scalar square root needs a bounded integer radicand"
                )
            return sp.sqrt(int(text))
        match = re.match(r"\d+(?:\.\d+)?", self.text[self.index :])
        if match is None:
            raise UnsupportedCondition("unsupported scalar exponent operand")
        self.index += match.end()
        return rational(match.group())


@dataclass(frozen=True)
class Exponent:
    value: object
    latex: str

    def times(self, other):
        if self.value == 1 and self.latex == "1":
            return other
        if other.value == 1 and other.latex == "1":
            return self
        return Exponent(
            self.value * other.value, rf"({self.latex})\cdot({other.latex})"
        )


def factor_base(value):
    value = Fraction(value)
    if value <= 0 or max(value.numerator, value.denominator) > 10**9:
        raise UnsupportedCondition(
            "the supported power bases must be positive bounded rationals"
        )
    result = {}
    for number, sign in ((value.numerator, 1), (value.denominator, -1)):
        for prime, count in sp.factorint(number).items():
            result[int(prime)] = [Exponent(sp.Integer(sign * count), str(sign * count))]
    return result


def combine(left, right, sign=1):
    result = {k: list(v) for k, v in left.items()}
    for base, terms in right.items():
        values = (
            terms
            if sign == 1
            else [Exponent(-t.value, "-(" + t.latex + ")") for t in terms]
        )
        result.setdefault(base, []).extend(values)
    return result


def raise_power(terms, exponent):
    return {base: [t.times(exponent) for t in values] for base, values in terms.items()}


def totals(terms):
    return {
        base: sp.simplify(sum((t.value for t in values), sp.Integer(0)))
        for base, values in terms.items()
    }


def exact_value(terms, bindings):
    substituted = {}
    for base, values in terms.items():
        if isinstance(base, str):
            if base not in bindings:
                raise UnsupportedCondition("an unassigned power variable remains")
            for prime, powers in factor_base(bindings[base]).items():
                substituted = combine(
                    substituted, {prime: [v.times(powers[0]) for v in values]}
                )
        else:
            substituted = combine(substituted, {base: values})
    result = Fraction(1)
    for prime, exponent in totals(substituted).items():
        if exponent.is_Integer is not True or abs(exponent) > 1000:
            raise UnsupportedCondition(
                "the prime powers do not give a bounded rational exact answer"
            )
        result *= Fraction(prime) ** int(exponent)
    return result, substituted
