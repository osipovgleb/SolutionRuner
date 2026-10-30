"""Optical ranges and the below-resonance branch reuse rational constraints."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .fraction_questions import A, B, Question, X, read_formula
from .physical_questions import scalar


def lens(match):
    values = {
        k: scalar(v.replace(" ", ""))
        for k, v in match.groupdict().items()
        if k not in ["left", "right", "image"]
    }
    if (
        any(v <= 0 for v in values.values())
        or values["near_min"] > values["near_max"]
        or values["far_min"] > values["far_max"]
    ):
        raise UnsupportedCondition(
            "positive ordered optical distance ranges are required"
        )
    aliases = {"d_1": "x", "d_2": "b", "f": "a"}
    _, left = read_formula(match["left"], aliases, 1 / X + 1 / B)
    _, right = read_formula(match["right"], aliases, 1 / A)
    denominators = []
    for denominator in left + right:
        if denominator == B:
            continue  # The entire screen range is strictly positive.
        if B in denominator.free_symbols:
            raise UnsupportedCondition(
                "a screen denominator must be the positive screen distance"
            )
        denominators.append(denominator.subs(A, values["focus"]))
    focus = values["focus"]
    domain = sp.Interval(values["near_min"], values["near_max"]).intersect(
        sp.Interval.open(focus, sp.oo)
    )
    if domain is sp.S.EmptySet:
        raise UnsupportedCondition("no positive real-image lens distance is feasible")
    denominators.append(X - focus)
    values["image"] = match["image"]
    return Question(
        "lens",
        focus * X / (X - focus),
        values["far_max"],
        "le",
        domain,
        "d_1",
        "см",
        values,
        tuple(denominators),
        match["left"] + "=" + match["right"],
        lower_target=values["far_min"],
    )


def resonance(match):
    values = {"resonant": scalar(match["resonant"]), "target": scalar(match["target"])}
    if values["resonant"] <= 0 or values["target"] < 0:
        raise UnsupportedCondition(
            "positive resonance and a nonnegative percentage are required"
        )
    law = B * A**2 / sp.Abs(A**2 - X**2)
    expression, denominators = read_formula(
        match["formula"], {"A_0": "b", r"\omega_p": "a", r"\omega": "x"}, law
    )
    # Only this explicitly below-resonance branch makes the modulus positive.
    expression = sp.cancel(expression.xreplace({sp.Abs(A**2 - X**2): A**2 - X**2}) / B)
    binding = {A: values["resonant"]}
    return Question(
        "resonance",
        expression.subs(binding),
        1 + values["target"] / 100,
        "le",
        sp.Interval.Ropen(0, values["resonant"]),
        r"\omega",
        r"с^{-1}",
        values,
        tuple(d.subs(binding) for d in denominators),
        match["formula"],
        maximum=True,
    )


def make_question(kind, match):
    return {"lens": lens, "resonance": resonance}[kind](match)
