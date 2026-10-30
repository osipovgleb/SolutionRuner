"""Square-root laws become rational constraints only after sign and unit checks."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .fraction_questions import A, B, Question, X
from .physical_questions import scalar
from .rational_formula import SquareRootFormulaParser, canonical_formula

_LAWS = {
    "root_acceleration": (sp.sqrt(2 * A * X), {"l": "a", "a": "x"}, 2 * A * X),
    "root_acceleration_min": (sp.sqrt(2 * A * X), {"l": "a", "a": "x"}, 2 * A * X),
    "root_distance": (sp.sqrt(2 * A * X), {"a": "a", "l": "x"}, 2 * A * X),
    "root_horizon": (sp.sqrt(A * X / 500), {"R": "a", "h": "x"}, A * X / 500),
    "root_horizon_km": (sp.sqrt(2 * A * X), {"R": "a", "h": "x"}, 2 * A * X),
    "root_steps": (sp.sqrt(A * X / 500), {"R": "a", "h": "x"}, A * X / 500),
    "root_rise": (sp.sqrt(A * X / 500), {"R": "a", "h": "x"}, A * X / 500),
    "rocket": (
        A * sp.sqrt(1 - X**2 / B**2),
        {"l_0": "a", "v": "x", "c": "b"},
        1 - X**2 / B**2,
    ),
}
_TEXT_FIELDS = {
    "formula",
    "path_unit",
    "answer_unit",
    "acceleration_unit",
    "speed_unit",
    "formal_path_unit",
    "declared_speed_unit",
}


def normalize(text):
    for unit in ["км", "ч", "с", "м"]:
        text = text.replace(r"\mathrm{" + unit + "}", unit)
    text = text.replace(r"\,", "").replace("·", r"\cdot")
    text = re.sub(r"l\s*_(?:\{0\}|0)", "l_0", text)
    text = text.replace("Расстояние(в км)от", "Расстояние(в км) от")
    text = re.sub(r"(?<=\d)(?=км/|м/)", " ", text)
    return text


def make_question(kind, match):
    law, aliases, radicand = _LAWS[kind]
    parser = SquareRootFormulaParser(
        canonical_formula(match["formula"], aliases), "xabde"
    )
    expression = parser.parse()
    if (
        len(parser.roots) != 1
        or sp.cancel(parser.roots[0] - radicand) != 0
        or sp.cancel(expression - law) != 0
    ):
        raise UnsupportedCondition(
            "the complete square-root formula must match its physical law"
        )
    values = {
        k: scalar("1" if v == "один" else v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in _TEXT_FIELDS and v is not None
    }
    if any(
        v < 0 or v == 0 and k not in ["target", "speed", "before"]
        for k, v in values.items()
    ):
        raise UnsupportedCondition(
            "positive physical parameters and nonnegative targets are required"
        )
    values.update(
        {
            k: v
            for k, v in match.groupdict().items()
            if k in _TEXT_FIELDS and k != "formula"
        }
    )
    values["kind"] = kind
    return _BUILDERS[kind](values, radicand, parser.denominators, match["formula"])


def question(
    values,
    expression,
    target,
    output,
    source,
    bindings,
    relation="eq",
    domain=None,
):
    label, unit = output
    denominators, formula = source
    return Question(
        values["kind"],
        sp.expand(expression.subs(bindings)),
        target,
        relation,
        sp.Interval(0, sp.oo) if domain is None else domain,
        label,
        unit,
        values,
        tuple(d.subs(bindings) for d in denominators),
        formula,
    )


def motion(v, radicand, denominators, formula):
    if v["speed_unit"] != v["acceleration_unit"]:
        raise UnsupportedCondition("speed and acceleration units must be consistent")
    native = "км" if v["speed_unit"] == "км/ч" else "м"
    v["native_unit"] = native
    if v["kind"] == "root_distance":
        declared = v.get("path_unit")
        if (
            declared
            and declared.strip(" ()").removeprefix("в ") != native
            or v.get("declared_speed_unit") not in [None, v["speed_unit"]]
        ):
            raise UnsupportedCondition("the declared path and speed units must agree")
        output = "км" if v["answer_unit"] == "километров" else "м"
        scale = (
            sp.Integer(1000)
            if native == "м" and output == "км"
            else sp.Rational(1, 1000)
            if native == "км" and output == "м"
            else sp.Integer(1)
        )
        return question(
            v,
            radicand.subs(X, scale * X),
            v["speed"] ** 2,
            ("l", output),
            (denominators, formula),
            {A: v["acceleration"]},
        )
    if (
        v["answer_unit"] != v["acceleration_unit"]
        or (v.get("formal_path_unit") or v["kind"] == "root_acceleration_min")
        and native != "км"
    ):
        raise UnsupportedCondition(
            "the acceleration answer and declared path units must agree"
        )
    given_unit = "м" if v["path_unit"] == "метров" else "км"
    v["native_path"] = v["path"] * (
        1000
        if given_unit == "км" and native == "м"
        else sp.Rational(1, 1000)
        if given_unit == "м" and native == "км"
        else 1
    )
    return question(
        v,
        radicand,
        v["speed"] ** 2,
        ("a", v["answer_unit"] + r"^{2}"),
        (denominators, formula),
        {A: v["native_path"]},
        "ge" if v["kind"] == "root_acceleration_min" else "eq",
        sp.Interval.open(0, sp.oo),
    )


def horizon(v, radicand, denominators, formula):
    if v["kind"] in ["root_steps", "root_rise"]:
        v["initial_height"] = 500 * v["before"] ** 2 / v["radius"]
        v["step_m"] = v["step"] / 100 if v["kind"] == "root_steps" else sp.Integer(1)
        radicand = radicand.subs(X, v["initial_height"] + v["step_m"] * X)
        label, unit, relation = (
            ("n", "ступенек", "ge")
            if v["kind"] == "root_steps"
            else (r"\Delta h", "м", "eq")
        )
        if v["kind"] == "root_rise" and v["target"] <= v["before"]:
            raise UnsupportedCondition(
                "the horizon distance must increase for an ascent"
            )
    else:
        label, unit, relation = (
            "h",
            "км" if v["kind"] == "root_horizon_km" else "м",
            "eq",
        )
    return question(
        v,
        radicand,
        v["target"] ** 2,
        (label, unit),
        (denominators, formula),
        {A: v["radius"]},
        relation,
    )


def rocket(v, radicand, denominators, formula):
    return question(
        v,
        radicand,
        (v["target"] / v["length"]) ** 2,
        ("v", "км/с"),
        (denominators, formula),
        {B: v["light"]},
        "le",
        sp.Interval.Ropen(0, v["light"]),
    )


_BUILDERS = {
    "root_acceleration": motion,
    "root_acceleration_min": motion,
    "root_distance": motion,
    "root_horizon": horizon,
    "root_horizon_km": horizon,
    "root_steps": horizon,
    "root_rise": horizon,
    "rocket": rocket,
}
