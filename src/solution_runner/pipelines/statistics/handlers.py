"""Shared statistical families, including verified diagram-based events."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = tuple(
    HandlerSpec(
        "statistics-" + key,
        "solution_runner.pipelines.statistics." + module + ":build_context_repair_plan",
        requires_parent_condition_asset=False,
    )
    for key, module in [
        ("moments", "moments"),
        ("waiting-times", "waiting"),
        ("estimates", "estimates"),
    ]
)

HANDLERS += (
    HandlerSpec(
        "statistics-euler-events",
        "solution_runner.pipelines.statistics.euler:build_context_repair_plan",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
        asset_selector="solution_runner.pipelines.statistics.euler:required_assets",
        diagram_builder="solution_runner.pipelines.statistics.euler:diagram_specs",
        inputs=(
            ("condition_asset_bytes", "condition_asset_bytes"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
    ),
    HandlerSpec(
        "statistics-symmetric-distribution",
        "solution_runner.pipelines.statistics.symmetry:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.statistics.symmetry:required_assets",
    ),
)
