"""Explicit bindings for reviewed spatial box distances."""

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
            "245359",
            "e0f344e7-9c1d-480f-b883-c1af2a31ebc8",
            19,
            "solid-box-distance-squared",
        ),
        (
            "245360",
            "ca9cb9d1-9dce-447d-8779-9796be5e7df4",
            20,
            "solid-box-vertex-distance",
        ),
        (
            "284357",
            "411d583a-a5ba-4a19-83ec-ab3fee2476c8",
            23,
            "solid-box-missing-edge",
        ),
        (
            "284363",
            "4687b808-47a2-4287-901e-eb602a4a3b60",
            24,
            "solid-box-space-diagonal",
        ),
    )
)
