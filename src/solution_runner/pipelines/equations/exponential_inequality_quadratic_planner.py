"""Prepare certified positive-power and factor proofs without source writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .exponential_inequality_cubic_figures import SOURCES as CUBIC_SOURCES
from .exponential_inequality_cubic_figures import chart as cubic_chart
from .exponential_inequality_factorization_proof import RENDERS as FACTORIZATION_PROOFS
from .exponential_inequality_factorizations import ANALYSES as FACTORIZATIONS
from .exponential_inequality_preimage_proof import METHODS as PREIMAGE_METHODS
from .exponential_inequality_preimage_proof import RENDERS as PREIMAGE_RENDERS
from .exponential_inequality_preimages import analyze as quadratic_exponent
from .exponential_inequality_quadratic import analyze_quadratic
from .exponential_inequality_quadratic_proof import METHODS, render
from .exponential_inequality_reduction_proof import RENDERS
from .exponential_inequality_reductions import ANALYSES as REDUCTIONS
from .exponential_nested_reciprocal import analyze as nested_reciprocal
from .exponential_nested_reciprocal_proof import render as nested_proof
from .exponential_reciprocal_sum import analyze as reciprocal_sum
from .exponential_reciprocal_sum import render as reciprocal_proof
from .exponential_squared_denominator import analyze as squared_denominator
from .exponential_squared_denominator_figures import SOURCES as SQUARED_SOURCES
from .exponential_squared_denominator_figures import chart as squared_chart
from .exponential_squared_denominator_proof import render as squared_proof
from .inequality_plan import repair
from .mixed_substitution_figures import SOURCES as MIXED_SOURCES
from .mixed_substitution_figures import chart
from .mixed_substitution_proof import model as mixed_model
from .mixed_substitution_proof import render as mixed_render
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/exponential-inequalities/positive-quadratics.json"
    ).read_text()
)
SOURCES.update(
    json.loads(
        (
            Path(__file__).parent
            / "assets/exponential-inequalities/factor-reductions.json"
        ).read_text()
    )
)
SOURCES.update(
    json.loads(
        (
            Path(__file__).parent
            / "assets/exponential-inequalities/factorized-signs.json"
        ).read_text()
    )
)
SOURCES.update(
    json.loads(
        (
            Path(__file__).parent
            / "assets/exponential-inequalities/quadratic-exponents.json"
        ).read_text()
    )
)
ANALYSES = {
    **dict.fromkeys(METHODS, analyze_quadratic),
    **REDUCTIONS,
    **dict.fromkeys(PREIMAGE_METHODS, quadratic_exponent),
    **FACTORIZATIONS,
    "mixed_substitution": mixed_model,
    "symmetric_reciprocal": reciprocal_sum,
    "nested_reciprocal": nested_reciprocal,
    "squared_denominator": squared_denominator,
}
SOURCES.update(
    json.loads(
        (
            Path(__file__).parent
            / "assets/exponential-inequalities/reciprocal-sums.json"
        ).read_text()
    )
)
SOURCES.update(MIXED_SOURCES["parents"])
SOURCES.update(
    json.loads(
        (
            Path(__file__).parent
            / "assets/exponential-inequalities/nested-reciprocal.json"
        ).read_text()
    )
)
SOURCES.update(CUBIC_SOURCES["parents"])
SOURCES.update(SQUARED_SOURCES["parents"])
PROOFS = {
    **RENDERS,
    **PREIMAGE_RENDERS,
    **FACTORIZATION_PROOFS,
    "symmetric_reciprocal": reciprocal_proof,
    "nested_reciprocal": nested_proof,
    "squared_denominator": squared_proof,
    "mixed_substitution": mixed_render,
}


def build_context_repair_plan(
    context, *, parent_solution_html="", method, generated_solution_assets=()
):
    if hashlib.sha256(parent_solution_html.encode()).hexdigest() not in SOURCES.get(
        method, ()
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent for this exponential method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets") and method not in (
        "mixed_substitution",
        "cube_over_square",
        "squared_denominator",
    ):
        raise UnsupportedCondition(
            "these reviewed exponential parents have no source diagrams"
        )
    a = ANALYSES[method](formula)
    if method in ("cube_over_square", "squared_denominator"):
        selected_chart = cubic_chart if method == "cube_over_square" else squared_chart
        image, keys, changes = selected_chart(context, a, generated_solution_assets)
        return repair(
            condition,
            answer,
            solution,
            a.answer,
            PROOFS[method](a, image),
            keys=keys,
            asset_changes=changes,
        )
    if method == "mixed_substitution":
        image, keys, changes = chart(context, a)
        return repair(
            condition,
            answer,
            solution,
            a.answer,
            PROOFS[method](a, image),
            keys=keys,
            asset_changes=changes,
        )
    html = render(a, method) if method in METHODS else PROOFS[method](a)
    return repair(condition, answer, solution, a.answer, html)
