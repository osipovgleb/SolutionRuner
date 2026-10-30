"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "vector-27663-coordinate-length",
        "solution_runner.pipelines.vectors.vector_length_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "vector-27707-rectangle-diagonal-length",
        "solution_runner.pipelines.vectors.rectangle_diagonal_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        inspect_current_asset_type=True,
    ),
    HandlerSpec(
        "vector-27708-rectangle-vector-sum-length",
        "solution_runner.pipelines.vectors.rectangle_vector_sum_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        inspect_current_asset_type=True,
    ),
    HandlerSpec(
        "vector-27718-rhombus-diagonal-difference",
        "solution_runner.pipelines.vectors.planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        inspect_current_asset_type=True,
    ),
)

HANDLERS += (
    HandlerSpec(
        "vector-coordinate-operations",
        "solution_runner.pipelines.vectors.coordinates:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += (
    HandlerSpec(
        "vector-metric-relations",
        "solution_runner.pipelines.vectors.metric_relations:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += (
    HandlerSpec(
        "vector-endpoint-coordinates",
        "solution_runner.pipelines.vectors.endpoints:build_context_repair_plan",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
        diagram_builder="solution_runner.pipelines.vectors.endpoints:diagram_specs",
        requires_parent_condition_asset=False,
    ),
)
