"""Prepare certified positive-power and factor proofs without source writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .exponential_inequality_factorization_proof import RENDERS as FACTORIZATION_PROOFS
from .exponential_inequality_factorizations import ANALYSES as FACTORIZATIONS
from .exponential_inequality_preimage_proof import METHODS as PREIMAGE_METHODS
from .exponential_inequality_preimage_proof import RENDERS as PREIMAGE_RENDERS
from .exponential_inequality_preimages import analyze as quadratic_exponent
from .exponential_inequality_quadratic import analyze_quadratic
from .exponential_inequality_quadratic_proof import METHODS, render
from .exponential_inequality_reduction_proof import RENDERS
from .exponential_inequality_reductions import ANALYSES as REDUCTIONS
from .inequality_plan import repair
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
}
PROOFS = {**RENDERS, **PREIMAGE_RENDERS, **FACTORIZATION_PROOFS}


def build_context_repair_plan(context, *, parent_solution_html="", method):
    if hashlib.sha256(parent_solution_html.encode()).hexdigest() not in SOURCES.get(
        method, ()
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent for this exponential method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "these reviewed exponential parents have no source diagrams"
        )
    a = ANALYSES[method](formula)
    html = render(a, method) if method in METHODS else PROOFS[method](a)
    return repair(condition, answer, solution, a.answer, html)
