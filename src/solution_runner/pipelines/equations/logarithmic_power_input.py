"""Read complete positive-variable powers with typed numeric and variable logarithms."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from . import logarithm_arithmetic as arithmetic
from .logarithm_parser import LogarithmParser, Node
from .power_arithmetic import ScalarParser, balanced
from .rational_inequality_parser import RationalParser, X
from .variable_logarithm_parser import VariableLogarithmParser

T = sp.Symbol("t", real=True)


class LogarithmicPowerParser(LogarithmParser):
    _argument = VariableLogarithmParser._argument

    def __init__(self, text, *, state=None, depth=0):
        text = re.sub(r"\\lg(?![a-zA-Z])", lambda _: r"\log_{10}", text)
        text = re.sub(r"\\log_([2-9])(?=\s|\^|\()", r"\\log_{\1}", text)
        super().__init__(text, depth)
        self.state = {"base": None, "logs": 0} if state is None else state
        self.denominators = []

    def _nested(self, text):
        return LogarithmicPowerParser(
            text, state=self.state, depth=self.depth + 1
        ).parse()

    def _combine(self, kind, left, right):
        if kind == "divide" and right.value.free_symbols:
            raise UnsupportedCondition(
                "original variable denominators are outside this power identity"
            )
        return super()._combine(kind, left, right)

    def _factor(self):
        if self.text[self.index : self.index + 1] in ("+", "-"):
            sign = self.text[self.index]
            self.index += 1
            value = self._factor()
            return (
                value
                if sign == "+"
                else Node(-value.value, "-" + value.text, "negative", (value,))
            )
        base = self._primary()
        if self.text[self.index : self.index + 1] != "^":
            return base
        exponent = self._exponent()
        if base.value != X and (
            base.value.is_Rational is not True
            or not 0 < base.value <= 10**6
            or base.value.q > 10**6
        ):
            raise UnsupportedCondition(
                "power bases must be the positive variable or bounded positive rationals"
            )
        if not exponent.value.free_symbols and (
            exponent.value.is_Rational is not True
            or abs(exponent.value) > 40
            or exponent.value.q > 20
        ):
            raise UnsupportedCondition("a bounded scalar power is required")
        value = sp.Pow(base.value, exponent.value, evaluate=False)
        return Node(
            value,
            "(" + base.text + ")^{" + exponent.text + "}",
            "power",
            (base, exponent),
        )

    def _primary(self):
        if self.text[self.index : self.index + 1] == "x":
            self.index += 1
            return Node(X, "x", "variable")
        if not self.text.startswith(r"\log_", self.index):
            return super()._primary()
        self.state["logs"] += 1
        if self.state["logs"] > 6:
            raise UnsupportedCondition("too many complete logarithm occurrences")
        self.index += 5
        raw, self.index = balanced(self.text, self.index)
        base = ScalarParser(raw).parse()
        if base.is_Rational is not True or not 1 < base <= 1000:
            raise UnsupportedCondition(
                "a bounded increasing numeric logarithm base is required"
            )
        power = 1
        if self.text[self.index : self.index + 1] == "^":
            power = self._exponent().value
            if power != 2:
                raise UnsupportedCondition(
                    "only the explicit logarithm square is reviewed"
                )
        reader = RationalParser(self._argument())
        argument = reader.parse().value
        if any(d.free_symbols for d in reader.denominators):
            raise UnsupportedCondition(
                "original logarithm-argument poles cannot be cancelled"
            )
        if argument == X:
            if self.state["base"] not in (None, base):
                raise UnsupportedCondition(
                    "all variable logarithms must use the same reference base"
                )
            self.state["base"] = base
            value = T
        elif argument.is_Rational is True and 0 < argument <= 10**6:
            value = arithmetic.log_ratio(base, argument)
        else:
            raise UnsupportedCondition(
                "a logarithm argument must be the complete variable or a positive rational constant"
            )
        text = (
            r"\log_{"
            + sp.latex(base)
            + "}"
            + ("^2" if power == 2 else "")
            + r"\left("
            + sp.latex(argument)
            + r"\right)"
        )
        return Node(value**power, text, "logarithm")
