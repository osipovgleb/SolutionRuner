"""Reuse the exact scalar grammar, retaining every original denominator."""

from ..equations.power_arithmetic import ScalarParser, balanced
from ..probability.common import UnsupportedCondition


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
            raise UnsupportedCondition("the linear-fraction formula must be rational")
        return super()._factor()
