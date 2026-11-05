"""Explicit bindings for actual rectangular-box sections."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        uid,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="3",
        theme_title="Прямоугольный параллелепипед",
        theme_order_index=1,
        snapshot_theme_id="44b3d94d-87c2-4c6b-891b-43ef7c133aed",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, uid, index, rule in (
        (
            "316552",
            "1aa2e24a-17ce-4abe-a86c-6a72c5f82959",
            26,
            "solid-box-vertical-section",
        ),
        (
            "324452",
            "24c27e62-fcb3-47e1-85a7-4c97e755933f",
            28,
            "solid-box-oblique-section",
        ),
    )
)
