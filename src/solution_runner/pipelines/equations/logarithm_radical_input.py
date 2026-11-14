"""Replace only complete same-base variable logarithms, retaining original argument poles."""

import re

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm
from .power_arithmetic import clean
from .rational_inequality_parser import RationalParser, X


def read(formula):
    text = clean(formula)
    pieces = []
    base = None
    count = 0
    while r"\log_" in text:
        count += 1
        if count > 4:
            raise UnsupportedCondition(
                "too many complete logarithms for this root quotient"
            )
        start = text.index(r"\log_")
        prefix = text[:start]
        if "x" in re.sub(r"\\[A-Za-z]+", "", prefix):
            raise UnsupportedCondition(
                "ordinary x outside the logarithmic coordinate is not supported"
            )
        denominators = []
        atom, power, end = logarithm(
            text,
            start,
            X,
            extended=True,
            argument_reader=lambda raw, original=denominators: (
                RationalParser(raw, original).parse().value
            ),
        )
        if (
            atom.argument != X
            or atom.root
            or any(d.free_symbols for d in denominators)
            or atom.base.is_Rational is not True
            or not 1 < atom.base <= 1000
            or (base is not None and atom.base != base)
        ):
            raise UnsupportedCondition(
                "complete variable arguments without hidden poles and one increasing rational logarithm base are required"
            )
        base = atom.base
        pieces.extend((prefix, "(x)" + ("^{2}" if power == 2 else "")))
        text = text[end:]
    if base is None or "x" in re.sub(r"\\[A-Za-z]+", "", text):
        raise UnsupportedCondition(
            "the entire variable dependence must belong to the same logarithmic coordinate"
        )
    pieces.append(text)
    return base, "".join(pieces)
