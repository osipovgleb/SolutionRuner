"""Shared applied-mathematics content rules."""

from ..core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "applied-polynomial-physical-model",
        "solution_runner.pipelines.applied.physical_polynomials:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)
