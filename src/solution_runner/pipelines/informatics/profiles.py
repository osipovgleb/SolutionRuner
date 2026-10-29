"""Audited source groups from the informatics catalog."""

from solution_runner.pipelines.core.profile_definitions import _profile


PROFILES = (
    _profile(
        "9364", "88cfe7e0-7597-46ad-b077-de5bf6b4d812", 1,
        catalog_snapshot_id="4b8ce070-551c-4697-9b42-11c2617966d8",
        category_key="11",
        theme_title="Пароли с дополнительными сведениями",
        theme_order_index=0,
        snapshot_theme_id="d33e913c-5954-41fa-ae91-fd9e11ae3114",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="informatics-password-extra-bytes",
        rewrite_existing_solution=True,
    ),
)
