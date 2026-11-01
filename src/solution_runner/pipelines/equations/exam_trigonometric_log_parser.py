"""Read fixed-base log factors without evaluating or cancelling their domains."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import ScalarParser, balanced


class Parser(ExamAngleParser):
    implicit_prefixes = (*ExamAngleParser.implicit_prefixes, r"\log")

    def __init__(self, text, atoms, denominators, logs, depth=0):
        super().__init__(text, atoms, denominators, depth)
        self.logs = logs

    def _nested(self, text):
        return Parser(
            text, self.atoms, self.denominators, self.logs, self.depth + 1
        ).parse()

    def _primary(self):
        if not self.text.startswith(r"\log_", self.index):
            return super()._primary()
        self.index += 5
        if self.text[self.index : self.index + 1] == "{":
            text, self.index = balanced(self.text, self.index)
        elif self.index < len(self.text) and self.text[self.index] in "23456789":
            text = self.text[self.index]
            self.index += 1
        else:
            raise UnsupportedCondition(
                "an explicit constant logarithm base is required"
            )
        base = ScalarParser(text).parse()
        if base.free_symbols or base.is_positive is not True or base == 1:
            raise UnsupportedCondition(
                "the log base must be positive and different from one"
            )
        before = len(self.logs)
        argument = self._factor().value
        if len(self.logs) != before:
            raise UnsupportedCondition("nested log factors require a separate method")
        if not argument.free_symbols or len(self.logs) >= 2:
            raise UnsupportedCondition("one or two variable log factors are required")
        symbol = sp.Symbol("L" + str(len(self.logs)), real=True)
        self.logs.append((symbol, base, argument))
        return Node(symbol, "", "log")
