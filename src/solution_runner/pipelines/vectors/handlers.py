"""Explicit handler declarations; adding a group needs no runtime branch."""
from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec('vector-27663-coordinate-length', 'solution_runner.pipelines.vectors.vector_length_planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'), ('parent_solution_html', 'parent_solution_html'), ('current_asset_content_type', 'current_asset_content_type')), requires_parent_condition_asset=False),
    HandlerSpec('vector-27707-rectangle-diagonal-length', 'solution_runner.pipelines.vectors.rectangle_diagonal_planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'), ('parent_solution_html', 'parent_solution_html'), ('current_asset_content_type', 'current_asset_content_type')), inspect_current_asset_type=True),
    HandlerSpec('vector-27708-rectangle-vector-sum-length', 'solution_runner.pipelines.vectors.rectangle_vector_sum_planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'), ('parent_solution_html', 'parent_solution_html'), ('current_asset_content_type', 'current_asset_content_type')), inspect_current_asset_type=True),
    HandlerSpec('vector-27718-rhombus-diagonal-difference', 'solution_runner.pipelines.vectors.planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'), ('parent_solution_html', 'parent_solution_html'), ('current_asset_content_type', 'current_asset_content_type')), inspect_current_asset_type=True),
)
