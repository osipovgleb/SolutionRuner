"""Keep bounded numeric variable powers typed while reading all three log arguments."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_input import AbsolutePowerReader
from .exam_logarithmic_input import SYMBOLS, logarithm
from .logarithm_parser import Node
from .radical_inequality_parser import RadicalParser
from .rational_inequality_parser import RationalParser
from .variable_logarithm_parser import VariableLogarithmParser


class FactoredArgumentParser(RadicalParser):
    def __init__(self, text, denominators, powers, depth=0):
        super().__init__(text, denominators, depth, radicands=powers)
        # Only the inherited bounded typed-symbol checker is reused; these are powers, not roots.
        self.powers = powers

    def _nested(self, text):
        return FactoredArgumentParser(
            text, self.denominators, self.powers, self.depth + 1
        ).parse()

    def _primary(self):
        if not re.match(r"(?:[2-9]|10)\^\{", self.text[self.index :]):
            return RationalParser._primary(self)
        reader = AbsolutePowerReader(self.text, {})
        node, self.index = reader.power(self.index)
        self.denominators.extend(reader.denominators)
        base, exponent = (c.value for c in node.children)
        exponent = sp.cancel(exponent)
        pair = (base, exponent)
        symbol = next((s for s, p in self.powers.items() if p == pair), None)
        if symbol is None:
            if len(self.powers) >= 3:
                raise UnsupportedCondition(
                    "at most three distinct whole variable powers are reviewed"
                )
            symbol = sp.Dummy("positive_power", positive=True)
            self.powers[symbol] = pair
        return Node(symbol, "", "power_atom")


class FactoredLogParser(VariableLogarithmParser):
    def __init__(self, text, *, atoms, powers, denominators=None, depth=0):
        text = re.sub(r"\\log_([2-9])(?=\s|\()", r"\\log_{\1}", text)
        super().__init__(text, atoms=atoms, denominators=denominators, depth=depth)
        self.powers = powers

    def _nested(self, text):
        return FactoredLogParser(
            text,
            atoms=self.atoms,
            powers=self.powers,
            denominators=self.denominators,
            depth=self.depth + 1,
        ).parse()

    def _primary(self):
        if not self.text.startswith(r"\log_", self.index):
            return RationalParser._primary(self)
        if len(self.atoms.values) >= 3:
            raise UnsupportedCondition(
                "only three complete logarithms belong to the parent identity"
            )
        atom, degree, self.index = logarithm(
            self.text,
            self.index,
            SYMBOLS[len(self.atoms.values)],
            argument_reader=lambda raw: (
                FactoredArgumentParser(
                    raw, self.denominators, self.powers, self.depth + 1
                )
                .parse()
                .value
            ),
            argument_powers=True,
        )
        if degree != 1 or atom.root:
            raise UnsupportedCondition(
                "outer logarithm squares and roots are outside the parent identity"
            )
        self.atoms.values.append(atom)
        return Node(atom.symbol, "", "logarithm")


def read_context(context):
    from bs4 import BeautifulSoup

    from .rational_inequality_figures import read_formula

    content = context.get("normalized_content")
    if not isinstance(content, dict) or not isinstance(content.get("sections"), list):
        return read_formula(context)
    conditions = [
        s
        for s in content["sections"]
        if isinstance(s, dict) and s.get("key") == "condition"
    ]
    if len(conditions) != 1:
        return read_formula(context)
    (original,) = conditions
    soup = BeautifulSoup(original.get("html", ""), "html.parser")
    for tag in list(soup.find_all(("center", "span"))):
        if tag.has_attr("data-inline-latex") and tag.get_text(strip=True):
            raise UnsupportedCondition(
                "the inline formula must have no conflicting visible text"
            )
        if not tag.attrs:
            tag.unwrap()
    condition = {**original, "html": str(soup)}
    prepared = {
        **context,
        "normalized_content": {
            **content,
            "sections": [
                condition if s is original else s for s in content["sections"]
            ],
        },
    }
    (_, _, answer, solution), formula = read_formula(prepared)
    return (content, original, answer, solution), formula
