"""Read two typed variable-base log atoms with all original argument denominators."""

import re
from dataclasses import dataclass, field

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import SYMBOLS, Atom
from .logarithm_parser import LogarithmParser, Node, combined
from .power_arithmetic import balanced
from .rational_inequality_parser import RationalParser


@dataclass
class Atoms:
    values: list = field(default_factory=list)


class VariableLogarithmParser(LogarithmParser):
    def __init__(self, text, *, atoms=None, denominators=None, depth=0):
        super().__init__(text, depth)
        self.atoms = atoms if atoms is not None else Atoms()
        self.denominators = denominators if denominators is not None else []

    def _nested(self, text):
        return VariableLogarithmParser(
            text, atoms=self.atoms, denominators=self.denominators, depth=self.depth + 1
        ).parse()

    @staticmethod
    def _combine(kind, left, right):
        if kind == "divide" and right.value.free_symbols:
            raise UnsupportedCondition(
                "outer logarithm denominators are outside this reviewed product"
            )
        return combined(kind, left, right)

    def _exponent(self):
        exponent = super()._exponent()
        if exponent.value.is_Integer is not True or not 0 <= exponent.value <= 2:
            raise UnsupportedCondition(
                "only nonnegative outer logarithm powers up to two are reviewed"
            )
        return exponent

    def _argument(self):
        start = self.index
        if self.text.startswith(r"\frac", start):
            _, end = balanced(self.text, start + 5)
            _, end = balanced(self.text, end)
            raw = self.text[start:end]
        elif self.text[start : start + 1] and self.text[start] in "({":
            char = self.text[start]
            raw, end = balanced(self.text, start, char, ")" if char == "(" else "}")
            raw = "(" + raw + ")"
        else:
            match = re.match(r"x|[0-9]+", self.text[start:])
            if match is None:
                raise UnsupportedCondition(
                    "a complete rational logarithm argument is required"
                )
            raw = match[0]
            end = start + len(raw)
        # In this reviewed notation a power after the argument belongs to that argument.
        if self.text[end : end + 1] == "^":
            if self.text[end + 1 : end + 2] == "{":
                exponent, end = balanced(self.text, end + 1)
            else:
                exponent = self.text[end + 1 : end + 2]
                end += 2
            raw += "^{" + exponent + "}"
        self.index = end
        return raw

    def _primary(self):
        if self.text.startswith(r"\sqrt", self.index):
            raise UnsupportedCondition("outer logarithm radicals are not reviewed")
        if not self.text.startswith(r"\log_", self.index):
            return super()._primary()
        if len(self.atoms.values) >= 2:
            raise UnsupportedCondition("at most two variable logarithms are reviewed")
        self.index += 5
        if self.text[self.index : self.index + 1] != "{":
            raise UnsupportedCondition(
                "the complete logarithm base needs explicit braces"
            )
        base, self.index = balanced(self.text, self.index)
        argument = self._argument()
        b = RationalParser(base, self.denominators).parse().value
        a = RationalParser(argument, self.denominators).parse().value
        atom = Atom(b, a, False, SYMBOLS[len(self.atoms.values)])
        self.atoms.values.append(atom)
        return Node(atom.symbol, "", "logarithm")
