"""Explicit bindings for two adjacent isosceles box-angle groups."""

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
            "245361",
            "8ddeba01-b26a-414e-bd17-01354ff628f6",
            21,
            "solid-box-angle-from-face-diagonal",
        ),
        (
            "245363",
            "f2d5e307-a5f8-45bf-ac16-a952216de42b",
            22,
            "solid-box-angle-from-base-diagonal",
        ),
    )
)
