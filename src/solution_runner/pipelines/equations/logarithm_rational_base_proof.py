"""Keep the parent's two pictured base cases and exact rational-argument domains."""

import hashlib

from ..probability.common import UnsupportedCondition
from ..word_problems.common import rewrite
from .expression_repair import with_condition_repair
from .inequality_plan import repair
from .logarithm_rational_base_cases import analyze
from .logarithm_rational_base_figures import SOURCES, canonical, charts
from .rational_inequality_figures import read_formula
from .single_log_three_methods_proof import case_proof


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed two-chart base-case parent is required"
        )
    (_, original, _, _), _ = read_formula(context)
    prepared, fixed = canonical(context)
    (_, condition, answer, solution), formula = read_formula(prepared)
    a = analyze(formula)
    images, keys, changes = charts(prepared, a, generated_solution_assets)
    html = case_proof(a.logarithm, heading=False, before_case_images=images)
    plan = repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
    return with_condition_repair(
        plan,
        rewrite(original, "condition", "Условие", fixed) if fixed is not None else None,
    )
