"""Prepare the reviewed positive-quadratic parent methods without source writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .exponential_inequality_quadratic import analyze_quadratic
from .exponential_inequality_quadratic_proof import render
from .inequality_plan import repair
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/exponential-inequalities/positive-quadratics.json"
    ).read_text()
)


def build_context_repair_plan(context, *, parent_solution_html="", method):
    if hashlib.sha256(parent_solution_html.encode()).hexdigest() not in SOURCES.get(
        method, ()
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent for this quadratic method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "these reviewed quadratic parents have no source diagrams"
        )
    a = analyze_quadratic(formula)
    return repair(condition, answer, solution, a.answer, render(a, method))
