"""Positive binary logarithm ratios and a checked half-life law."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .log_patterns import PATTERNS
from .physical_questions import scalar
from .rational_formula import RationalFormulaParser, canonical_formula

A, B, D, E, F, G, X = sp.symbols("a b d e f g x", real=True)
DECAY_LAW = r"m_0\cdot2^{-\frac{t}{T}}"
BROKEN_DECAY_LAW = r"m_0\cdot2^{-t}\divT"
_LAWS = {
    "capacitor": (
        A * B * D,
        E / X,
        {r"\alpha": "a", "R": "b", "C": "d", "U_0": "e", "U": "x"},
        {A: "alpha", B: "resistance", D: "capacity", E: "initial"},
    ),
    "water": (
        A * B * D / E,
        (F - G) / (X - G),
        {
            r"\alpha": "a",
            "c": "b",
            "m": "d",
            r"\gamma": "e",
            "T_water": "f",
            "T_room": "g",
            "T": "x",
        },
        {
            A: "alpha",
            B: "heat",
            D: "mass_flow",
            E: "transfer",
            F: "initial",
            G: "offset",
        },
    ),
    "bell_volume": (
        A * B * D,
        E / X,
        {r"\alpha": "a", "v": "b", "T": "d", "V_1": "e", "V_2": "x"},
        {A: "alpha", B: "amount", D: "temperature", E: "initial"},
    ),
    "bell_pressure": (
        A * B * D,
        X / E,
        {r"\alpha": "a", "v": "b", "T": "d", "p_1": "e", "p_2": "x"},
        {A: "alpha", B: "amount", D: "temperature", E: "initial"},
    ),
}


@dataclass(frozen=True)
class Question:
    kind: str
    scale: sp.Rational
    values: dict
    formula: str
    repair_decay: bool = False
    maximum: bool = False


def normalize(text):
    text = (
        text.replace(r"\,", "")
        .replace("α", r"\alpha")
        .replace(r"\alpha\nu", r"\alpha v")
        .replace(r"\nu", "v")
    )
    for unit in ["C", "Дж", "Вт", "кг", "с"]:
        text = text.replace(r"\mathrm{" + unit + "}", unit)
    text = text.replace(r"T_{\mathrm{п}}", "T_room").replace(
        r"T_{\mathrm{в}}", "T_water"
    )
    text = re.sub(
        r"([mUVp])\s*_(?:\{([012])\}|([012]))",
        lambda m: m[1] + "_" + (m[2] or m[3]),
        text,
    )
    return text


def make_question(kind, match):
    values = {
        k: scalar(v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in ["formula", "maximum"] and v is not None
    }
    for key, value in values.items():
        if key in ["offset", "initial"] and kind == "water":
            continue
        if value < 0 or value == 0 and key != "level":
            raise UnsupportedCondition(
                "positive log parameters and nonnegative time, distance or work are required"
            )
    if kind == "decay":
        formula = re.sub(r"\s+", "", match["formula"])
        if formula not in [DECAY_LAW, BROKEN_DECAY_LAW]:
            raise UnsupportedCondition(
                "the formula must be the half-life law or its audited malformed rendering"
            )
        if values["target"] > values["initial"]:
            raise UnsupportedCondition("future decay cannot increase the initial mass")
        return Question(
            kind, values["period"], values, DECAY_LAW, formula == BROKEN_DECAY_LAW
        )
    coefficient, argument, aliases, names = _LAWS[kind]
    parts = re.fullmatch(r"(.+?)\\log_(?:\{\(2\)\}|\{2\}|2)\s+(.+)", match["formula"])
    if not parts:
        raise UnsupportedCondition("one binary logarithm of a ratio is required")
    parsers = [
        RationalFormulaParser(canonical_formula(raw, aliases), "xabdefg")
        for raw in parts.groups()
    ]
    parsed = [p.parse() for p in parsers]
    if sp.cancel(parsed[0] - coefficient) != 0 or sp.cancel(parsed[1] - argument) != 0:
        raise UnsupportedCondition(
            "the logarithmic formula contradicts its declared law"
        )
    bindings = {symbol: values[name] for symbol, name in names.items()}
    offset = values.get("offset", sp.Integer(0))
    if values["initial"] <= offset:
        raise UnsupportedCondition(
            "the initial quantity must exceed its logarithmic offset"
        )
    domain = (
        sp.Interval(values["initial"], sp.oo)
        if kind == "bell_pressure"
        else sp.Interval.Lopen(offset, values["initial"])
    )
    for denominator in [d for p in parsers for d in p.denominators]:
        bound = sp.cancel(denominator.subs(bindings))
        numerator = sp.fraction(sp.together(bound))[0]
        if numerator == 0 or numerator.free_symbols - {X}:
            raise UnsupportedCondition(
                "an original logarithmic denominator is zero or unassigned"
            )
        if X in numerator.free_symbols:
            poly = sp.Poly(numerator, X)
            if (
                poly.degree() != 1
                or domain.contains(-poly.nth(0) / poly.nth(1)) is sp.S.true
            ):
                raise UnsupportedCondition(
                    "an original denominator vanishes in the physical domain"
                )
    return Question(
        kind,
        sp.cancel(parsed[0].subs(bindings)),
        values,
        match["formula"],
        maximum=bool(match.groupdict().get("maximum")),
    )


def parse(text):
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(normalize(text))
        if match:
            question = make_question(kind, match)
            question.values["source_values"] = {
                k: v.replace(" ", "")
                for k, v in match.groupdict().items()
                if k not in ["formula", "maximum"] and v is not None
            }
            if kind in ["bell_volume", "bell_pressure"]:
                question.values["amount_symbol"] = r"\nu" if r"\nu" in text else "v"
            return question
    raise UnsupportedCondition(
        "the complete logarithmic-ratio question must be recognized"
    )
