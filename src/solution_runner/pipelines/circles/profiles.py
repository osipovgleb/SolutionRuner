"""Explicit bindings for the central and inscribed angle theme."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        identifier,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="1",
        theme_title="Центральные и вписанные углы",
        theme_order_index=5,
        snapshot_theme_id="61827edd-c190-47fd-8f5a-eb1c67f50529",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, identifier, index, rule in (
        (
            "245385",
            "c5747482-24b1-45b1-afed-fe5c8e4a3c5e",
            1,
            "circle-central-angle-difference",
        ),
        (
            "27863",
            "54adf235-496d-4ab3-b324-9f85fc8fd37e",
            4,
            "circle-inscribed-angle-difference",
        ),
        (
            "27864",
            "b1315d05-f467-4c4a-8895-112b53ee5a5f",
            5,
            "circle-inscribed-angle-arc-fraction",
        ),
        (
            "27866",
            "ae7e27ec-8d9f-487c-94bb-67dbe4116962",
            6,
            "circle-inscribed-angle-two-arcs",
        ),
        (
            "27869",
            "ae11fb35-cd29-4a36-8a1d-9087768aab27",
            7,
            "circle-diameters-inscribed-to-central",
        ),
        (
            "27870",
            "9fd6c378-9316-4ba5-a90d-5174b5fe18db",
            8,
            "circle-diameters-central-to-inscribed",
        ),
        (
            "27886",
            "fe5407fd-b5ad-4576-a7ae-b0895618a0f9",
            10,
            "circle-secant-angle-arc-difference",
        ),
    )
)
