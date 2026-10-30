"""Typed physical laws with exactly one declared trigonometric atom."""

import re
from dataclasses import dataclass, replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from . import power_units
from .angle_patterns import PATTERNS
from .physical_questions import scalar
from .rational_formula import RationalFormulaParser, canonical_formula

A, B, D, E, X = sp.symbols("a b d e x", real=True)
_SPECS = {
    "power": (
        A * B * X,
        {"F": "a", "v": "b"},
        {A: "force", B: "speed"},
        "cos",
        1,
        "eq",
        False,
        "N",
    ),
    "height": (
        A**2 * (1 - X) / (4 * B),
        {"v_0": "a", "g": "b"},
        {A: "speed", B: "gravity"},
        "cos",
        1,
        "ge",
        False,
        "H",
    ),
    "range": (
        A**2 * X / B,
        {"v_0": "a", "g": "b"},
        {A: "speed", B: "gravity"},
        "sin",
        1,
        "ge",
        False,
        "L",
    ),
    "collision": (
        A * B**2 * X**2,
        {"m": "a", "v": "b"},
        {A: "mass", B: "speed"},
        "sin",
        2,
        "ge",
        False,
        "Q",
    ),
    "boat": (
        A * X / B,
        {"L": "a", "u": "b"},
        {A: "width", B: "current"},
        "ctg",
        1,
        "le",
        False,
        "t",
    ),
    "platform": (
        A * D * X / (A + B),
        {"m": "a", "M": "b", "v": "d"},
        {A: "mass", B: "platform", D: "speed"},
        "cos",
        1,
        "ge",
        True,
        "u",
    ),
    "flight": (
        2 * A * X / B,
        {"v_0": "a", "g": "b"},
        {A: "speed", B: "gravity"},
        "sin",
        1,
        "eq",
        False,
        "t",
    ),
    "ampere": (
        A * B * D * E**2 * X,
        {"N": "a", "I": "b", "B": "d", "l": "e"},
        {A: "turns", B: "current", D: "field", E: "side"},
        "sin",
        1,
        "ge",
        False,
        "M",
    ),
    "lorentz": (
        A * B * D * X,
        {"q": "a", "v": "b", "B": "d"},
        {A: "charge", B: "speed", D: "field"},
        "sin",
        1,
        "ge",
        False,
        r"F_{\mathrm{л}}",
    ),
    "faraday": (
        A * B * X,
        {"a": "a", "S": "b"},
        {A: "rate", B: "area"},
        "cos",
        1,
        "le",
        False,
        r"\mathcal{E}_i",
    ),
    "work": (
        A * B * X,
        {"F": "a", "S": "b"},
        {A: "force", B: "distance"},
        "cos",
        1,
        "ge",
        True,
        "A",
    ),
}
_ATOM = re.compile(
    r"\\(?P<function>sin|cos|ctg)(?:\^(?:\{(?P<braced>[12])\}|(?P<plain>[12])))?\s*(?P<scale>2\s*)?(?P<angle>\\(?:alpha|beta|varphi))"
)
_ACUTE = sp.Interval.open(0, 90)
_DOMAINS = {
    "collision": sp.Interval.Lopen(0, 90),
    "flight": sp.Interval.Lopen(0, 90),
    "lorentz": sp.Interval(0, 180),
}


@dataclass(frozen=True)
class Question:
    kind: str
    expression: sp.Expr
    target: sp.Rational
    function: str
    power: int
    angle: str
    domain: sp.Interval
    relation: str
    maximum: bool
    quantity: str
    values: dict
    denominators: tuple
    formula: str
    multiplier: int = 1
    argument_multiplier: int = 1


def normalize(text):
    for letter, command in [("α", r"\alpha"), ("β", r"\beta"), ("φ", r"\varphi")]:
        text = text.replace(letter, command)
    for unit in ["Тл", "Кл", "Н", "В", "м", "с", "A"]:
        text = text.replace(r"\mathrm{" + unit + "}", unit)
    text = text.replace(r"\,", "").replace("·", r"\cdot")
    text = (
        text.replace(r"F_{\mathrm{л}}", "F_L")
        .replace(r"\mathcal{E}_i", "E_i")
        .replace(r"\epsilon_i", "E_i")
    )
    text = text.replace("3находящегося", "находящегося")
    text = re.sub(r"(?<=[\d}])(?=(?:Кл|Тл|Н|В|м/с|м\^\{2\})(?:\s|[,.?/]))", " ", text)
    text = re.sub(r"\s+([.?])", r"\1", text)
    return text


def formula(raw, aliases, expected, trig_atom):
    function, exponent, angle, scale = trig_atom
    if "@" in raw:
        raise UnsupportedCondition("a reserved angle marker is not valid source math")
    matches = list(_ATOM.finditer(raw))
    if len(matches) != 1:
        raise UnsupportedCondition("exactly one trigonometric angle atom is required")
    atom = matches[0]
    power = int(atom["braced"] or atom["plain"] or 1)
    if (
        atom["function"] != function
        or atom["angle"] != angle
        or power != exponent
        or int(atom["scale"] or 1) != scale
    ):
        raise UnsupportedCondition(
            "the trigonometric function, power, argument scale and declared angle must agree"
        )
    replaced = raw[: atom.start()] + "@^{" + str(power) + "}" + raw[atom.end() :]
    parser = RationalFormulaParser(
        canonical_formula(replaced, aliases).replace("@", "x"), "xabde"
    )
    parsed = parser.parse()
    if sp.cancel(parsed - expected) != 0:
        raise UnsupportedCondition(
            "the formula contradicts its declared physical angle law"
        )
    return parsed, parser.denominators


def make_question(kind, match):
    values = {
        k: scalar(v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in ["formula", "left", "right", "angle", "order", "unit"]
    }
    if any(
        v < 0 or v == 0 and key not in ["target", "clearance"]
        for key, v in values.items()
    ):
        raise UnsupportedCondition(
            "positive physical parameters and nonnegative target are required"
        )
    angle = match.groupdict().get("angle", r"\alpha")
    if kind == "height":
        values["target"] = values["wall"] + values["clearance"]
    if kind == "power":
        values["repair_unit"] = power_units.needs_repair(match["unit"])
    if kind == "diffraction":
        values["order"] = {"второй": 2, "третий": 3}[match["order"]]
        _, denominators = formula(
            match["left"],
            {"d": "d", "k": "a", r"\lambda": "b"},
            D * X,
            ("sin", 1, angle, 1),
        )
        right = RationalFormulaParser(
            canonical_formula(match["right"], {"k": "a", r"\lambda": "b"}), "ab"
        )
        if sp.cancel(right.parse() - A * B) != 0:
            raise UnsupportedCondition(
                "the diffraction maximum must equal order times wavelength"
            )
        expression = values["order"] * values["wavelength"] / X
        return Question(
            kind,
            expression,
            values["target"],
            "sin",
            1,
            angle,
            _ACUTE,
            "le",
            False,
            "d",
            values,
            tuple(denominators + right.denominators + [X]),
            match["left"] + "=" + match["right"],
        )
    law, aliases, names, function, power, relation, maximum, quantity = _SPECS[kind]
    argument_multiplier = 2 if kind in ["height", "range"] else 1
    parsed, denominators = formula(
        match["formula"], aliases, law, (function, power, angle, argument_multiplier)
    )
    bindings = {symbol: values[key] for symbol, key in names.items()}
    if kind == "ampere" and values["turns"].is_Integer is not True:
        raise UnsupportedCondition("the coil turn count must be a positive integer")
    return Question(
        kind,
        sp.cancel(parsed.subs(bindings)),
        values["target"],
        function,
        power,
        angle,
        _DOMAINS.get(kind, _ACUTE),
        relation,
        maximum,
        quantity,
        values,
        tuple(d.subs(bindings) for d in denominators),
        match["formula"],
        2 if kind == "collision" else 1,
        argument_multiplier,
    )


def parse(text):
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(normalize(text))
        if match:
            question = make_question(kind, match)
            if kind == "faraday" and r"\epsilon_i" in text:
                question = replace(question, quantity=r"\epsilon_i")
            question.values["source_values"] = {
                k: re.sub(r"(?<=\d),(?=\d)", "{,}", v.replace(" ", ""))
                for k, v in match.groupdict().items()
                if k not in ["formula", "left", "right", "angle", "order", "unit"]
            }
            if kind == "height":
                question.values["source_values"]["target"] = sp.latex(question.target)
            return question
    raise UnsupportedCondition("the complete static-angle question must be recognized")


def given_symbols(q):
    if q.kind == "diffraction":
        return {
            "k": str(q.values["order"]),
            r"\lambda": q.values["source_values"]["wavelength"],
        }
    _, aliases, names, *_ = _SPECS[q.kind]
    return {
        alias: q.values["source_values"][names[sp.Symbol(name, real=True)]]
        for alias, name in aliases.items()
    }
