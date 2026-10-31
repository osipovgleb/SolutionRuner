"""Exact component balances for solutions, alloys and conserved dry matter."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability.common import UnsupportedCondition, finish
from . import math_common, mixture_proof
from .mixture_questions import Question, parse

M1, M2, C1, C2, X = sp.symbols("m_1 m_2 c_1 c_2 x", real=True)


@dataclass(frozen=True)
class Analysis:
    question: Question
    result: sp.Rational
    amounts: tuple = ()
    fractions: tuple = ()
    equations: tuple = ()
    roots: tuple = ()


def positive(*values):
    if any(value <= 0 for value in values):
        raise UnsupportedCondition("positive component amounts are required")


def fractions(q):
    return tuple(q.values[key] / 100 for key in ["p1", "p2"])


def linear_pair(equations, variables):
    matrix, right = sp.linear_eq_to_matrix(equations, variables)
    if matrix.det() == 0:
        raise UnsupportedCondition(
            "the component balances must determine one unique solution"
        )
    return tuple(matrix.inv() * right)


def mean(q):
    v = q.values
    positive(v["a1"])
    if v["a2"] < 0 or v["a2"] == 0 and q.kind != "dilution":
        raise UnsupportedCondition(
            "positive mixture amounts or nonnegative added water are required"
        )
    c1, c2 = fractions(q)
    result = 100 * (v["a1"] * c1 + v["a2"] * c2) / (v["a1"] + v["a2"])
    return Analysis(q, result, (v["a1"], v["a2"]), (c1, c2))


def drying(q):
    v = q.values
    positive(v["final_mass"])
    if not v["raisin_water"] < v["grape_water"] < 100:
        raise UnsupportedCondition(
            "drying must remove water while preserving nonzero dry matter"
        )
    before, after = 1 - v["grape_water"] / 100, 1 - v["raisin_water"] / 100
    original = v["final_mass"] * after / before
    return Analysis(q, original, (original, v["final_mass"]), (before, after))


def alloy(q):
    v = q.values
    c1, c2 = fractions(q)
    if q.kind == "alloy_total":
        positive(v["total"])
        size = M1 + M2 - v["total"]
        total = v["total"]
    else:
        positive(v["difference"])
        size = M2 - M1 - v["difference"]
        total = M1 + M2
    concentration = c1 * M1 + c2 * M2 - v["target"] * total / 100
    equations = (size, concentration)
    masses = linear_pair(equations, (M1, M2))
    positive(*masses)
    result = masses[1] - masses[0] if q.kind == "alloy_total" else sum(masses)
    positive(result)
    return Analysis(q, result, masses, (c1, c2), equations)


def two_scenarios(q):
    v = q.values
    positive(v["water"], v["added"])
    c1, c2 = fractions(q)
    base = c1 * M1 + c2 * M2
    equations = (
        base - v["target"] * (M1 + M2 + v["water"]) / 100,
        base
        + v["added"] * v["alternative"] / 100
        - v["second_target"] * (M1 + M2 + v["added"]) / 100,
    )
    masses = linear_pair(equations, (M1, M2))
    positive(*masses)
    return Analysis(q, masses[0], masses, (c1, c2), equations)


def unknown_concentrations(q):
    v = q.values
    positive(v["a1"], v["a2"])
    equations = (
        C1 + C2 - 2 * v["mean"] / 100,
        v["a1"] * C1 + v["a2"] * C2 - (v["a1"] + v["a2"]) * v["target"] / 100,
    )
    concentrations = linear_pair(equations, (C1, C2))
    if (
        any(not 0 <= c <= 1 for c in concentrations)
        or concentrations[0] == concentrations[1]
    ):
        raise UnsupportedCondition(
            "two distinct physical concentrations between zero and one are required"
        )
    return Analysis(
        q, v["a1"] * concentrations[0], (v["a1"], v["a2"]), concentrations, equations
    )


def ratio(q):
    v = q.values
    positive(v["r1"], v["r2"], v["target"])
    scale = 2 * v["target"] / (v["r1"] + v["r2"])
    concentrations = (v["r1"] * scale / 100, v["r2"] * scale / 100)
    if any(c > 1 for c in concentrations):
        raise UnsupportedCondition(
            "derived concentrations cannot exceed one hundred percent"
        )
    return Analysis(
        q,
        100 * (concentrations[1] - concentrations[0]),
        (sp.Integer(1), sp.Integer(1)),
        concentrations,
    )


def acid_difference(q):
    v = q.values
    positive(v["acid1"], v["acid2"], v["total"])
    difference = v["difference"] / 100
    if not 0 < difference < 1 or v["acid1"] + v["acid2"] > v["total"]:
        raise UnsupportedCondition(
            "the acid masses and positive concentration difference must be physical"
        )
    polynomial = (
        v["total"] * X * (X - difference)
        - v["acid1"] * (X - difference)
        - v["acid2"] * X
    )
    roots = tuple(real_roots(polynomial, X))
    valid = [r for r in roots if difference < r <= 1]
    if len(valid) != 1 or valid[0].is_Rational is not True:
        raise UnsupportedCondition(
            "one exact rational physical concentration is required without rounding"
        )
    c1 = valid[0]
    masses = (v["acid1"] / c1, v["acid2"] / (c1 - difference))
    return Analysis(q, 100 * c1, masses, (c1, c1 - difference), (polynomial,), roots)


_CALCULATORS = {
    "dilution": mean,
    "equal": mean,
    "weighted": mean,
    "drying": drying,
    "alloy_total": alloy,
    "alloy_difference": alloy,
    "two_scenarios": two_scenarios,
    "unknown_concentrations": unknown_concentrations,
    "ratio": ratio,
    "acid_difference": acid_difference,
}


def analyze(question):
    return _CALCULATORS[question.kind](question)


def calculate(context):
    data = math_common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    return finish(
        condition, ans, solution, answer(analysis.result), mixture_proof.proof(analysis)
    )
