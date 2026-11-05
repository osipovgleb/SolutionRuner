"""Explicit bindings for all seven eligible sphere groups."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        uid,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="3",
        theme_title="Шар",
        theme_order_index=10,
        snapshot_theme_id="ee9144aa-f4c1-4377-a436-7c1ab0055a91",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, uid, index, rule in (
        (
            "27059",
            "649a0bf3-cbb6-48d8-8908-99bd8ecfc589",
            0,
            "solid-sphere-great-circle-surface",
        ),
        (
            "27072",
            "6e6383b3-a1b2-435c-a4f2-d42de126e2ee",
            1,
            "solid-sphere-surface-from-radius-ratio",
        ),
        (
            "27097",
            "a57cfc48-a629-473b-812e-53e877feb218",
            2,
            "solid-sphere-volume-factor",
        ),
        (
            "27125",
            "106905e5-1fa0-4fa9-9267-3a850970fc8c",
            3,
            "solid-sphere-sum-volumes-radius",
        ),
        (
            "27162",
            "191c8df9-2bca-42b4-8018-999bbae698c9",
            4,
            "solid-sphere-surface-from-volume-ratio",
        ),
        (
            "27163",
            "7110dad8-8730-4d3c-abfe-3a3b0753d08d",
            5,
            "solid-sphere-sum-surfaces-radius",
        ),
        (
            "27174",
            "864b2c71-a817-4bbc-bcb2-5573b52ce7ec",
            6,
            "solid-sphere-surface-from-pi-volume",
        ),
    )
)
