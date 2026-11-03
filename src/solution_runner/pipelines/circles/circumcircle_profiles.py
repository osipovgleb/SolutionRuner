"""Explicit bindings for circumcircle lengths and radii."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        identifier,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="1",
        theme_title="Описанные окружности",
        theme_order_index=8,
        snapshot_theme_id="dde26ca5-b012-4e0a-99d2-feec2c147fd6",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, identifier, index, rule in (
        (
            "27892",
            "b7e8fd2a-398e-4f2e-8cab-faee5b6fc913",
            6,
            "circle-circumcircle-equilateral-radius-side",
        ),
        (
            "27893",
            "f0ad1c67-ecf7-4b7c-b615-f0eda1e170b1",
            7,
            "circle-circumcircle-equilateral-side-radius",
        ),
        (
            "27894",
            "00a7216a-0b8d-411c-bd1a-965bf730f925",
            8,
            "circle-circumcircle-equilateral-radius-height",
        ),
        (
            "27895",
            "1aca2d8a-1f6e-4f85-a57f-887a0d50ccfb",
            9,
            "circle-circumcircle-equilateral-height-radius",
        ),
    )
)
