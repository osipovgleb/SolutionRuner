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


PROFILES += tuple(
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
            "27896",
            "7334b112-62ed-46b5-a6fb-26a7afebd1e8",
            10,
            "circle-circumcircle-right-radius-hypotenuse",
        ),
        (
            "27897",
            "28323c4b-8871-4a4b-ad12-b86a0cb1865c",
            11,
            "circle-circumcircle-right-hypotenuse-radius",
        ),
        (
            "27898",
            "740c3948-12f6-48f0-814a-b47be5c227d2",
            12,
            "circle-circumcircle-right-radius-legs",
        ),
        (
            "27900",
            "2ce7ed6a-d1ca-4f12-93ed-987108281e10",
            13,
            "circle-circumcircle-isosceles-diameter-120",
        ),
        (
            "27906",
            "14e17c28-81e1-4f50-aa82-7225c7e32a14",
            14,
            "circle-circumcircle-hexagon-side-radius",
        ),
        (
            "27918",
            "d2a0e4d1-2045-498c-91df-6a9e15b01887",
            15,
            "circle-circumcircle-sine-radius-30",
        ),
        (
            "27920",
            "f5a30663-fa49-4fad-b6e8-3717abff823b",
            17,
            "circle-circumcircle-sine-side",
        ),
        (
            "27921",
            "1de41a80-3559-47be-a699-95baee1502f1",
            18,
            "circle-circumcircle-sine-radius-150",
        ),
        (
            "27929",
            "988b7d5b-0ff6-4d52-b716-9d28efc20800",
            25,
            "circle-circumcircle-hexagon-diameter-perimeter",
        ),
    )
)
