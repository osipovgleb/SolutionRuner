"""Group bindings for this domain; handler implementations live separately."""
from solution_runner.pipelines.core.profile_definitions import (
    _profile,
)

PROFILES = (
    _profile(
                "77152", "913dd919-8d79-4ddc-be8c-f87a128e04c9", 25,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="1", theme_title="Трапеция",
                theme_order_index=4, snapshot_theme_id="4b4fdec3-28d2-4d56-b662-9795d37d443b",
                expected_vertices=None, strategy_key=None, workflow_kind="content_rule",
                content_rule_key="trapezoid-77152-isosceles-leg-from-sine",
                rewrite_existing_solution=True,
                condition_asset_id="324c1800-e987-4e60-9cb7-f41cc3d0254c",
                condition_asset_sha256="7a40fc7067bd9d2358cd717894f3eb0a62ecb4b3dd573278137f2f58c863236d",
            ),
)
