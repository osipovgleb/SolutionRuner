"""Prepare a certified logarithmic inequality solution without source writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .inequality_plan import repair
from .logarithm_product_inequality import analyze
from .logarithm_product_inequality_proof import render
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/product-comparison.json"
    ).read_text()
)


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parent_sha256"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithm product parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "this reviewed logarithm product parent has no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
