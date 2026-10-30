"""Trigonometric atoms extend the existing typed numeric arithmetic grammar."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_parser import LogarithmParser, Node
from .power_arithmetic import balanced
from .trig_angles import TrigAtom, parse_angle, signs


class TrigonometricParser(LogarithmParser):
    def __init__(self, text, atoms=None, denominators=None, depth=0):
        super().__init__(text, depth)
        self.atoms = {} if atoms is None else atoms
        self.denominators = [] if denominators is None else denominators

    def _nested(self, text):
        return TrigonometricParser(
            text, self.atoms, self.denominators, self.depth + 1
        ).parse()

    def _combine(self, kind, left, right):
        a, b = left.value, right.value
        if kind == "divide":
            if b.is_zero is True:
                raise UnsupportedCondition(
                    "division by zero in the original expression"
                )
            self.denominators.append(b)
        result = {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
        }[kind]()
        return Node(result, "", "arithmetic", (left, right))

    def _product(self):
        value = self._factor()
        while self.index < len(self.text):
            kind = "multiply"
            for op in (r"\cdot", r"\times", r"\colon", r"\div", "*", "/"):
                if self.text.startswith(op, self.index):
                    self.index += len(op)
                    kind = "divide" if op in (r"\colon", r"\div", "/") else "multiply"
                    break
            else:
                if not (
                    self.text[self.index] == "("
                    or self.text.startswith(
                        (r"\sin", r"\cos", r"\tg", r"\ctg", r"\sqrt"), self.index
                    )
                ):
                    break
            value = self._combine(kind, value, self._factor())
        return value

    def _primary(self):
        function = re.match(r"\\(sin|cos|tg|ctg)", self.text[self.index :])
        if not function:
            if self.text.startswith(r"\log", self.index):
                raise UnsupportedCondition(
                    "logarithms are outside this trigonometric method"
                )
            return super()._primary()
        start = self.index
        self.index += function.end()
        exponent = (
            self._exponent().value
            if self.text[self.index : self.index + 1] == "^"
            else sp.Integer(1)
        )
        if exponent.is_Integer is not True or not 1 <= exponent <= 4:
            raise UnsupportedCondition(
                "a small positive trigonometric power is required"
            )
        angle_start = self.index
        if self.text[self.index : self.index + 1] == "(":
            _, self.index = balanced(self.text, self.index, "(", ")")
        elif self.text.startswith(r"\frac", self.index):
            self.index += 5
            _, self.index = balanced(self.text, self.index)
            _, self.index = balanced(self.text, self.index)
        else:
            match = re.match(
                r"(?:[+-]?\d+)?\\pi|[+-]?\d+(?:\.\d+)?", self.text[self.index :]
            )
            if not match:
                raise UnsupportedCondition(
                    "an explicit numeric trigonometric angle is required"
                )
            self.index += match.end()
        for suffix in [r"^{\circ}", r"^\circ"]:
            if self.text.startswith(suffix, self.index):
                self.index += len(suffix)
                break
        angle = self.text[angle_start : self.index]
        q, degrees = parse_angle(angle)
        function = function[1]
        sign = signs(function, q)
        symbol = (
            sp.Symbol("T" + str(len(self.atoms)), zero=True)
            if sign == 0
            else sp.Symbol(
                "T" + str(len(self.atoms)), positive=sign > 0, negative=sign < 0
            )
        )
        text = "\\" + function + "(" + angle + ")"
        if len(self.atoms) >= 24:
            raise UnsupportedCondition(
                "the trigonometric expression has too many atoms"
            )
        self.atoms[symbol] = TrigAtom(function, q, degrees, text)
        return Node(symbol**exponent, self.text[start : self.index], "trig")
