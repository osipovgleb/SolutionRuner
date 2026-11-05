"""Category-fifteen bindings reuse the shared spatial-distance runtime."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        uid,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="15",
        theme_title=title,
        theme_order_index=theme_index,
        snapshot_theme_id=theme,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, uid, index, title, theme_index, theme, rule in (
        (
            "514520",
            "e9c955ef-0a43-4706-9d5a-2e55cb63adb5",
            1,
            "Расстояние между прямыми и плоскостями",
            0,
            "6d3f432b-504b-4551-938f-27f974c15bf5",
            "solid-pyramid-skew-midpoint-distance",
        ),
        (
            "501396",
            "0ca6e02c-36ba-4919-9201-18bbd77dfe68",
            15,
            "Расстояние между точками, от точки до прямой",
            1,
            "f66b7523-bb9d-49bc-9664-1239a9cb9269",
            "solid-box-altitude-distance-comparison",
        ),
    )
)
