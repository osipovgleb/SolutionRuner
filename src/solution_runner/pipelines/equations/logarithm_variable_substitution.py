"""Change monomial variable bases before the shared rational logarithm substitution."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm
from .logarithm_arithmetic import log_ratio
from .logarithm_factor_arguments import read_polynomial
from .logarithm_rational_substitution import analyze_transformed
from .power_arithmetic import balanced, clean
from .rational_inequality_parser import X


@dataclass(frozen=True)
class VariableLog:
    original: str
    base: sp.Expr
    argument: sp.Expr
    numerator: sp.Expr
    denominator: sp.Expr

    @property
    def replacement(self):
        if self.denominator == 1:
            return "(" + sp.latex(self.numerator) + ")"
        return (
            r"\frac{"
            + sp.latex(self.numerator)
            + "}{"
            + sp.latex(self.denominator)
            + "}"
        )


def monomial(text):
    value, _ = read_polynomial(text)
    p = sp.Poly(value, X)
    if len(p.terms()) != 1 or p.degree() > 1 or p.LC() <= 0:
        raise UnsupportedCondition(
            "one positive constant or positive linear monomial is required"
        )
    return value


def complete_atom(text):
    if text[5:6] == "{":
        _, index = balanced(text, 5)
    elif text[5:6] in "23456789" and len(text) > 5:
        index = 6
    else:
        raise UnsupportedCondition("one complete numeric or monomial base is required")
    start = index
    if text[start : start + 1] == "(":
        raw, end = balanced(text, start, "(", ")")
    elif text.startswith(r"\frac", start):
        _, index = balanced(text, start + 5)
        _, end = balanced(text, index)
        raw = text[start:end]
    else:
        match = re.match(r"(?:[0-9]+(?:\.[0-9]+)?)?x|[0-9]+(?:\.[0-9]+)?", text[start:])
        if not match:
            raise UnsupportedCondition(
                "one complete numeric or monomial argument is required"
            )
        raw, end = match.group(), start + match.end()
    if text[end : end + 1] == "^":
        raise UnsupportedCondition(
            "argument or logarithm postfix powers are outside this presentation"
        )
    normalized = text[:start] + "(" + raw + ")"
    atom, power, consumed = logarithm(
        normalized, 0, X, extended=True, argument_reader=monomial
    )
    if power != 1 or atom.root or consumed != len(normalized):
        raise UnsupportedCondition("the whole monomial logarithm must be consumed")
    monomial(sp.latex(atom.base))
    return atom, text[:end], end


def linear(value, base):
    (degree,), coefficient = sp.Poly(value, X).terms()[0]
    shift = log_ratio(base, coefficient)
    if shift.is_Rational is not True or abs(shift) > 20:
        raise UnsupportedCondition(
            "each coefficient must be a bounded exact reference-base power"
        )
    return degree * X + shift


def read_input(formula):
    formula = re.sub(r"\\log_([2-9])(?=\s)", r"\\log_{\1}", formula)
    text = clean(formula.removesuffix("."))
    pieces, outside, atoms = [], [], []
    while r"\log_" in text:
        if len(atoms) >= 12:
            raise UnsupportedCondition("too many logarithm occurrences")
        start = text.index(r"\log_")
        pieces.append(text[:start])
        outside.append(text[:start])
        atom, original, end = complete_atom(text[start:])
        atoms.append((atom, original))
        pieces.append(None)
        text = text[start + end :]
    pieces.append(text)
    outside.append(text)
    fixed = {a.base for a, _ in atoms if not a.base.free_symbols}
    if len(fixed) != 1 or not any(a.base.has(X) for a, _ in atoms):
        raise UnsupportedCondition(
            "one common numeric reference and a positive linear variable base are required"
        )
    base = next(iter(fixed))
    if base <= 1 or base.is_Rational is not True or max(base.p, base.q) > 1000:
        raise UnsupportedCondition(
            "one bounded increasing rational reference base is required"
        )
    if re.search("x", re.sub(r"\\[a-zA-Z]+", "", "".join(outside))):
        raise UnsupportedCondition(
            "the original variable may occur only inside complete logarithms"
        )
    terms = []
    for i, (atom, original) in enumerate(atoms):
        numerator = linear(atom.argument, base)
        denominator = linear(atom.base, base)
        if denominator == 0:
            raise UnsupportedCondition("a logarithm base cannot be identically one")
        term = VariableLog(original, atom.base, atom.argument, numerator, denominator)
        terms.append(term)
        pieces[2 * i + 1] = term.replacement
    return base, tuple(terms), "".join(pieces)


def analyze(formula):
    return analyze_transformed(*read_input(formula))
