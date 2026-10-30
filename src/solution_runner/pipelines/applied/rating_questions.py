"""Typed rating laws, cross-checked prose weights and original denominators."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .physical_questions import scalar
from .rating_patterns import PATTERNS
from .rational_formula import RationalFormulaParser, canonical_formula

A, B, D, E, X = sp.symbols("a b d e x", real=True)
_WEIGHTS = {
    "вдвое": 2,
    "втрое": 3,
    "вчетверо": 4,
    "впятеро": 5,
    "вшестеро": 6,
    "всемеро": 7,
    "ввосьмеро": 8,
    "вдевятеро": 9,
    "вдесятеро": 10,
}
_ALIASES = {"In": "a", "Op": "b", "Tr": "d", "Q": "e", "A": "x"}
_STORE_ALIASES = {"r_b": "a", "r_e": "b", "K": "d"}
POWER_LAW = r"r_b-\frac{r_b-r_e}{(K+1)^{m}}"


@dataclass(frozen=True)
class Question:
    kind: str
    formula: str
    values: dict
    repair_weight: bool = False


def normalize(text):
    for suffix, alias in [("пок", "b"), ("экс", "e")]:
        text = re.sub(
            r"r\s*_(?:\{\\(?:mathrm|text)\{" + suffix + r"\}\}|" + suffix + ")",
            "r_" + alias,
            text,
        )
        text = re.sub(r"\br\s+" + suffix + r"\b", "r_" + alias, text)
    return re.sub(r"\s+([,.?])", r"\1", text.replace("макси-мальны", "максимальны"))


def weighted_formula(raw):
    renamed = re.sub(
        r"(?<![A-Za-z])(?:In|Op|Tr|Q|A)(?![A-Za-z])", lambda m: _ALIASES[m[0]], raw
    )
    parser = RationalFormulaParser(
        canonical_formula(renamed, {v: v for v in _ALIASES.values()}), "xabde"
    )
    expression = parser.parse()
    for denominator in parser.denominators:
        if (
            denominator.free_symbols - {X}
            or not denominator.is_polynomial(X)
            or len(sp.Poly(denominator, X).terms()) != 1
        ):
            raise UnsupportedCondition(
                "weighted ratings require original denominators nonzero for every positive A"
            )
    return expression


def weighted(kind, match):
    lower, upper = scalar(match["lower"]), scalar(match["upper"])
    if not lower.is_Integer or not upper.is_Integer or lower > upper:
        raise UnsupportedCondition("an ordered integer rating scale is required")
    if match.groupdict().get("scale") and int(match["scale"]) != upper - lower + 1:
        raise UnsupportedCondition("the stated scale length contradicts its endpoints")
    if match["information"] not in _WEIGHTS or match["objectivity"] not in _WEIGHTS:
        raise UnsupportedCondition("the relative rating weights must be recognized")
    weights = (
        _WEIGHTS[match["information"]],
        1,
        _WEIGHTS[match["objectivity"]],
        0 if kind == "three_max" else 1,
    )
    expression = weighted_formula(match["formula"])
    expected = sum(w * s for w, s in zip(weights, (A, B, D, E), strict=True)) / X
    repair = (
        kind == "identity"
        and (lower, upper) == (0, 4)
        and weights == (5, 1, 3, 1)
        and sp.cancel(expression - (5 * A + B + 4 * D + E) / X) == 0
    )
    if repair:
        weights = (5, 1, 4, 1)
    elif sp.cancel(expression - expected) != 0:
        raise UnsupportedCondition(
            "the printed rating formula contradicts its prose weights"
        )
    target = None if kind == "identity" else scalar(match["target"])
    return Question(
        kind,
        match["formula"],
        {"lower": lower, "upper": upper, "weights": weights, "target": target},
        repair,
    )


def numeric_denominators(parser, values):
    for denominator in parser.denominators:
        bound = sp.cancel(denominator.subs(values))
        if bound.free_symbols or bound == 0:
            raise UnsupportedCondition(
                "an original store-rating denominator is zero or unassigned"
            )


def store(kind, match):
    values = {k: scalar(match[k]) for k in ["count", "buyer", "expert"]}
    k, buyer, expert = (values[key] for key in ["count", "buyer", "expert"])
    if not k.is_Integer or k < 0 or buyer + sp.Rational(1, 10) <= 0:
        raise UnsupportedCondition(
            "a nonnegative integer customer count and positive exponent denominator are required"
        )
    if kind == "store_product" and not (
        0 <= buyer <= 1 and 0 <= expert <= sp.Rational(7, 10)
    ):
        raise UnsupportedCondition(
            "the customer and expert ratings must lie in their stated ranges"
        )
    raw = match["exponent"] if kind == "store_power" else match["formula"]
    parser = RationalFormulaParser(canonical_formula(raw, _STORE_ALIASES), "abd")
    expression = parser.parse()
    exponent = D / (50 * (A + sp.Rational(1, 10)))
    expected = exponent if kind == "store_power" else A - (A - B) / ((D + 1) * exponent)
    if (
        sp.cancel(expression - expected) != 0
        or kind == "store_power"
        and re.sub(r"\s+", "", match["formula"]) != POWER_LAW
    ):
        raise UnsupportedCondition(
            "the printed customer/expert rating law must be preserved"
        )
    numeric_denominators(parser, {A: buyer, B: expert, D: k})
    return Question(kind, match["formula"], values)


def parse(text):
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(normalize(text))
        if match:
            return (
                store(kind, match)
                if kind.startswith("store_")
                else weighted(kind, match)
            )
    raise UnsupportedCondition("the complete rating question must be recognized")
