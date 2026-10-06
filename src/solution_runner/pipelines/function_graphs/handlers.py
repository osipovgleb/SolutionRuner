"""Declarations for the function-graph domain."""
from ..core.handlers import HandlerSpec

HANDLERS = tuple(
    HandlerSpec(
        key=f'hyperbola-shift-{mode}',
        target='solution_runner.pipelines.function_graphs.hyperbola:build_context_repair_plan',
        inputs=(('condition_asset_bytes', 'condition_asset_bytes'),
                ('current_asset_content_type', 'current_asset_content_type')),
        options=(('mode', mode.removeprefix('horizontal-')),)+((('horizontal_model',True),) if mode.startswith('horizontal-') else ()),
        requires_parent_condition_asset=False,
        inspect_current_asset_type=True,
        requires_condition_asset_download=True,
        allow_non_svg_condition_asset=True,
        asset_selector='solution_runner.pipelines.function_graphs.diagrams:required_assets',
    )
    for mode in ('value', 'argument', 'horizontal-value', 'horizontal-argument')
)


HANDLERS += (HandlerSpec(
    key='hyperbola-shift-fractional-coefficient',
    target='solution_runner.pipelines.function_graphs.fractional_hyperbola:build_context_repair_plan',
    inputs=(('condition_asset_bytes','condition_asset_bytes'),('current_asset_content_type','current_asset_content_type')),
    requires_parent_condition_asset=False,
    inspect_current_asset_type=True,
    requires_condition_asset_download=True,
    asset_selector='solution_runner.pipelines.function_graphs.fractional_hyperbola:required_assets',
),)
