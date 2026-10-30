"""Bind audited linear-fraction laws to full questions and physical domains."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .fraction_patterns import PATTERNS
from .physical_questions import scalar
from .rational_formula import RationalFormulaParser

X, A, B, D, E = sp.symbols("x a b d e", real=True)
_LAWS = {
    "train": (
        A / (1 - X / B),
        {"f_0": "a", "v": "x", "c": "b"},
        {"frequency": A, "sound": B},
        "v",
        "м/с",
    ),
    "short_circuit": (
        E / (X + A),
        {r"\epsilon": "e", "R": "x", "r": "a"},
        {"internal": A},
        "R",
        "Ом",
    ),
    "parallel": (
        A * X / (A + X),
        {"R_1": "a", "R_2": "x"},
        {"resistance": A},
        "R_2",
        "Ом",
    ),
    "engine": (100 * (X - A) / X, {"T_1": "x", "T_2": "a"}, {"cold": A}, "T_1", "К"),
    "load": (
        E * X / (X + A),
        {r"\epsilon": "e", "R": "x", "r": "a"},
        {"voltage": E, "internal": A},
        "R",
        "Ом",
    ),
    "medium": (
        A * (X + B) / (X - D),
        {"f_0": "a", "c": "x", "u": "b", "v": "d"},
        {"frequency": A, "receiver": B, "source": D},
        "c",
        "м/с",
    ),
    "sonar": (
        B * (X - A) / (X + A),
        {"f_0": "a", "f": "x", "c": "b"},
        {"frequency": A, "sound": B},
        "f",
        "МГц",
    ),
}

# Lower/upper parameter names and whether the corresponding endpoint is open.
_DOMAINS = {
    "train": (None, "sound", False, True),
    "parallel": (None, None, True, True),
    "engine": ("cold", None, False, True),
    "medium": ("source", None, True, True),
    "sonar": ("frequency", None, False, True),
}


@dataclass(frozen=True)
class Question:
    kind: str
    expression: sp.Expr
    target: sp.Rational
    relation: str
    domain: sp.Interval
    label: str
    unit: str
    values: dict
    denominators: tuple
    formula: str
    maximum: bool = False


def normalize(text):
    text = text.replace(r"\,", "").replace(r"\%", "%")
    for unit in ["Ом", "К"]:
        text = text.replace(r"\mathrm{" + unit + "}", unit)
    text = re.sub(r"(?<=\d)Ом", " Ом", text)
    text = text.replace(r"\nu", "v").replace("ν", "v")
    text = text.replace("ульт-развуковые", "ультразвуковые").replace(
        "приемни-ком", "приемником"
    )
    text = re.sub(
        r"([fRT])\s*_(?:\{([012])\}|([012]))",
        lambda m: m[1] + "_" + (m[2] or m[3]),
        text,
    )
    return text


def read_formula(raw, aliases, expected):
    def substitute(match):
        token = match[0]
        if token in aliases:
            return aliases[token]
        if token in [r"\frac", r"\cdot"]:
            return token
        raise UnsupportedCondition("an undeclared physical formula variable remains")

    canonical = re.sub(
        r"\\[a-zA-Z]+|[A-Za-z](?:_\d)?",
        substitute,
        raw,
    )
    canonical = re.sub(r"([xabde])\s*(?=\\frac)", r"\1\\cdot ", canonical)
    parser = RationalFormulaParser(canonical, "xabde")
    expression = parser.parse()
    if sp.cancel(expression - expected) != 0:
        raise UnsupportedCondition("the formula contradicts its declared physical law")
    return expression, parser.denominators


def make_question(kind, match):
    equal = kind == "medium_equal"
    kind = "medium" if equal else kind
    law, aliases, names, label, unit = _LAWS[kind]
    values = {
        k: scalar(v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in ["formula", "short"]
    }
    for key, value in values.items():
        if (
            value < 0
            or value == 0
            and key not in ["target", "gap", "receiver", "source"]
        ):
            raise UnsupportedCondition(
                "positive physical parameters and nonnegative thresholds are required"
            )
    expression, denominators = read_formula(match["formula"], aliases, law)
    target = values.get("target", values.get("frequency", 0) + values.get("gap", 0))
    if kind == "short_circuit":
        short, extra = read_formula(match["short"], aliases, E / A)
        expression = sp.cancel(expression / short)
        denominators += extra
        target /= 100
    bindings = {symbol: values[key] for key, symbol in names.items()}
    expression = sp.cancel(expression.subs(bindings))
    denominators = tuple(sp.cancel(d.subs(bindings)) for d in denominators)
    lower, upper, left_open, right_open = _DOMAINS.get(kind, (None, None, False, True))
    domain = sp.Interval(
        values[lower] if lower else 0,
        values[upper] if upper else sp.oo,
        left_open=left_open,
        right_open=right_open,
    )
    relation = (
        "eq" if equal or kind == "sonar" else "le" if kind == "short_circuit" else "ge"
    )
    return Question(
        kind,
        expression,
        target,
        relation,
        domain,
        label,
        unit,
        values,
        denominators,
        match["formula"],
        kind == "medium" and not equal,
    )


def parse(text):
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(normalize(text))
        if match:
            return make_question(kind, match)
    raise UnsupportedCondition(
        "the complete linear-fraction question must be recognized"
    )
