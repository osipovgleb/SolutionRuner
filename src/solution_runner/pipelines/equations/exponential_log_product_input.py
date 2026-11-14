"""Read a whole exponential factor and a typed quadratic logarithm factor."""

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import SYMBOLS, logarithm
from .exponential_inequality_parser import ExponentialParser
from .logarithm_parser import LogarithmParser, Node, combined
from .rational_inequality_parser import RationalParser
from .variable_logarithm_parser import Atoms


class ExponentialLogProductParser(ExponentialParser):
    _product = LogarithmParser._product

    def __init__(self, text, denominators=None, depth=0, atoms=None):
        super().__init__(text, denominators, depth)
        self.atoms = Atoms() if atoms is None else atoms

    def _nested(self, text):
        if r"\log_" not in text:
            return ExponentialParser(text, self.denominators, self.depth + 1).parse()
        return ExponentialLogProductParser(
            text, self.denominators, self.depth + 1, self.atoms
        ).parse()

    def _combine(self, kind, left, right):
        if kind == "divide" and right.value.free_symbols:
            raise UnsupportedCondition(
                "outer variable denominators are outside the reviewed product"
            )
        return combined(kind, left, right)

    def _primary(self):
        if not self.text.startswith(r"\log_", self.index):
            return super()._primary()
        if len(self.atoms.values) >= 2:
            raise UnsupportedCondition("two complete logarithms are required")
        start = self.index
        atom, power, self.index = logarithm(
            self.text,
            self.index,
            SYMBOLS[len(self.atoms.values)],
            extended=True,
            argument_reader=lambda raw: (
                RationalParser(raw, self.denominators).parse().value
            ),
        )
        self.atoms.values.append(atom)
        return Node(atom.symbol**power, self.text[start : self.index], "logarithm")
