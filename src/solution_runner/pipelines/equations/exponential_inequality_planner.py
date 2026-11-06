"""Prepare common-base inequality solutions from a certified parent without writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import compare
from .exponential_inequality_proof import render
from .inequality_plan import repair
from .rational_inequality import set_latex
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (Path(__file__).parent / "assets/exponential-inequalities/sources.json").read_text()
)


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parent_sha256"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed common-base parent solution is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "this reviewed common-base family has no source diagrams"
        )
    a = compare(formula)
    return repair(condition, answer, solution, set_latex(a.stage.solution), render(a))
