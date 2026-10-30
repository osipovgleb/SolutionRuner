"""Shared applied-mathematics content rules."""

from ..core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "applied-linear-fraction",
        "solution_runner.pipelines.applied.linear_fractions:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-algebraic-formula",
        "solution_runner.pipelines.applied.algebraic_formulas:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-polynomial-physical-model",
        "solution_runner.pipelines.applied.physical_polynomials:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)
