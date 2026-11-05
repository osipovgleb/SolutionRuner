"""Explicit bindings for reviewed central, prism and pyramid volume families."""

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
            "27209",
            "2033b5b7-71f9-42a0-ac2f-4cffea82dd99",
            13,
            "solid-polyhedron-central-tetrahedron",
        ),
        (
            "245335",
            "e04e82d5-b585-4446-b62e-f360fbc460a1",
            14,
            "solid-polyhedron-half-box",
        ),
        (
            "245338",
            "3d1d1b2e-a4b5-431c-b8f3-5aa139b1357f",
            17,
            "solid-polyhedron-pyramid-with-note",
        ),
        (
            "245339",
            "169629c3-039e-4266-be5d-2c59c2ec8b10",
            18,
            "solid-polyhedron-triangle-pyramid",
        ),
        (
            "639664",
            "69bbbceb-4610-439a-a31c-01bd7a69d08b",
            29,
            "solid-polyhedron-face-pyramid",
        ),
    )
)
