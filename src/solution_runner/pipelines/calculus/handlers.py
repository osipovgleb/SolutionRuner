"""Shared analytic calculus families, selected independently of group numbers."""

from ..core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "calculus-graph-marked-points",
        "solution_runner.pipelines.calculus.graph_marked_points:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_marked_points:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_marked_points:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "calculus-graph-monotonic",
        "solution_runner.pipelines.calculus.graph_monotonic:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_monotonic:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_monotonic:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
        allow_non_svg_condition_asset=True,
    ),
    HandlerSpec(
        "calculus-graph-extrema",
        "solution_runner.pipelines.calculus.graph_extrema:build_context_repair_plan",
        inputs=(("condition_asset_bytes", "condition_asset_bytes"),),
        asset_selector="solution_runner.pipelines.calculus.graph_extrema:required_assets",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "calculus-graph-derivative-level",
        "solution_runner.pipelines.calculus.graph_derivative_levels:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_derivative_levels:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_derivative_levels:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "calculus-graph-stationary-points",
        "solution_runner.pipelines.calculus.graph_stationary:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_stationary:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_stationary:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "calculus-graph-composite-tangent",
        "solution_runner.pipelines.calculus.graph_composites:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_composites:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_composites:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "calculus-graph-tangent-slope",
        "solution_runner.pipelines.calculus.graph_tangents:build_context_repair_plan",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.calculus.graph_tangents:required_assets",
        diagram_builder="solution_runner.pipelines.calculus.graph_tangents:diagram_specs",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
    ),
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
