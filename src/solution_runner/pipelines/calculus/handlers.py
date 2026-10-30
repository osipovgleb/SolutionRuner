"""Shared analytic calculus families, selected independently of group numbers."""

from ..core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "calculus-polynomial-motion",
        "solution_runner.pipelines.calculus.motion:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "calculus-polynomial-tangency",
        "solution_runner.pipelines.calculus.tangency:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "calculus-polynomial-tangency-two-methods",
        "solution_runner.pipelines.calculus.tangency:build_context_repair_plan",
        options=(("two_methods", True),),
        requires_parent_condition_asset=False,
    ),
)
