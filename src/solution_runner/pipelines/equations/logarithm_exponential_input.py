"""Read affine outer coefficients and typed exponential logarithm arguments."""

import re

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import SYMBOLS, Atom
from .exponential_inequality_parser import ExponentialParser
from .logarithm_parser import Node
from .power_arithmetic import balanced
from .rational_inequality_parser import RationalParser
from .variable_logarithm_parser import VariableLogarithmParser


class ExponentialLogParser(VariableLogarithmParser):
    def __init__(self, text, **kwargs):
        text = re.sub(r"\\log_([2-9])(?=\s|\()", r"\\log_{\1}", text)
        super().__init__(re.sub(r"(?<=\d)(?=x)", r"\\cdot ", text), **kwargs)

    def _nested(self, text):
        return ExponentialLogParser(
            text, atoms=self.atoms, denominators=self.denominators, depth=self.depth + 1
        ).parse()

    def _primary(self):
        if not self.text.startswith(r"\log_", self.index):
            return RationalParser._primary(self)
        if len(self.atoms.values) >= 2:
            raise UnsupportedCondition(
                "at most two logarithms belong to this parent method"
            )
        self.index += 5
        if self.text[self.index : self.index + 1] != "{":
            raise UnsupportedCondition("the complete logarithm base is required")
        raw, self.index = balanced(self.text, self.index)
        base = RationalParser(raw, self.denominators).parse()
        argument = ExponentialParser(self._argument(), self.denominators).parse()
        atom = Atom(base.value, argument.value, False, SYMBOLS[len(self.atoms.values)])
        self.atoms.values.append(atom)
        return Node(atom.symbol, "", "logarithm", (base, argument))
