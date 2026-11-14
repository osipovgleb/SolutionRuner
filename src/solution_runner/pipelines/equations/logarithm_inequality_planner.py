"""Prepare a certified logarithmic inequality solution without source writes."""

import hashlib
import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .inequality_plan import repair
from .logarithm_product_inequality import analyze
from .logarithm_product_inequality_proof import render
from .logarithm_quadratic_inequality import analyze as quadratic
from .logarithm_quadratic_inequality_proof import render as quadratic_proof
from .logarithm_quotient_inequality_figures import SOURCES as QUOTIENT_SOURCES
from .logarithm_quotient_inequality_figures import chart
from .logarithm_quotient_inequality_proof import render as quotient_proof
from .rational_inequality_figures import read_formula, reviewed_asset

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/product-comparison.json"
    ).read_text()
)
PARENTS = {
    **dict.fromkeys(SOURCES["parent_sha256"], "product"),
    **dict.fromkeys(QUOTIENT_SOURCES["parent_sha256"], "quotient"),
}
QUADRATIC_SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/quadratic-comparison.json"
    ).read_text()
)
PARENTS.update(dict.fromkeys(QUADRATIC_SOURCES["parent_sha256"], "quadratic"))
SUBSTITUTION_SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/quadratic-substitution.json"
    ).read_text()
)
PARENTS.update(
    dict.fromkeys(SUBSTITUTION_SOURCES["parent_sha256"], "quadratic_substitution")
)


def substitution_assets(content, condition):
    assets = content.get("assets", [])
    if len(assets) > 1 or condition.get("asset_keys"):
        raise UnsupportedCondition("the substitution parent has no condition figures")
    for asset in assets:
        reviewed_asset(asset, figures=SUBSTITUTION_SOURCES["unused_solution_figures"])
        if asset["asset_id"] in condition["html"]:
            raise UnsupportedCondition(
                "the reviewed child-only chart must belong to the solution"
            )


def build_context_repair_plan(context, *, parent_solution_html="", method="product"):
    if PARENTS.get(hashlib.sha256(parent_solution_html.encode()).hexdigest()) != method:
        raise UnsupportedCondition(
            "the complete reviewed logarithm product parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if method in ("quadratic", "quadratic_substitution"):
        if method == "quadratic_substitution":
            substitution_assets(content, condition)
        elif content.get("assets"):
            raise UnsupportedCondition(
                "this direct quadratic parent has no source figures"
            )
        a = quadratic(formula)
        return repair(
            condition, answer, solution, a.answer, quadratic_proof(a, method=method)
        )
    if method == "product" and content.get("assets"):
        raise UnsupportedCondition(
            "this reviewed logarithm product parent has no source figures"
        )
    a = analyze(formula, method=method)
    if method == "quotient":
        image, keys, changes, scope = chart(context, a)
        return repair(
            condition,
            answer,
            solution,
            a.answer,
            quotient_proof(a, image, scope),
            keys=keys,
            asset_changes=changes,
        )
    return repair(condition, answer, solution, a.answer, render(a))
