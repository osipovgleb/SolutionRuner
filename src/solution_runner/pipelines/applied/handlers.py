"""Shared applied-mathematics content rules."""

from ..core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "applied-rating-model",
        "solution_runner.pipelines.applied.rating_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-harmonic-window",
        "solution_runner.pipelines.applied.harmonic_windows:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-harmonic-energy",
        "solution_runner.pipelines.applied.harmonic_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-static-angle-model",
        "solution_runner.pipelines.applied.angle_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-binary-log-ratio",
        "solution_runner.pipelines.applied.log_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-positive-gas-power",
        "solution_runner.pipelines.applied.gas_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "applied-rational-physical-model",
        "solution_runner.pipelines.applied.rational_models:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.applied.rational_models:required_assets",
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
        asset_selector="solution_runner.pipelines.applied.physical_polynomials:required_assets",
    ),
)
