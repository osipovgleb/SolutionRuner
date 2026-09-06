"""Group bindings for this domain; handler implementations live separately."""
from solution_runner.pipelines.core.profile_definitions import (
    _profile,
)

PROFILES = (
    _profile(
                "27663",
                "9e75ee4e-534e-4c70-b364-586e57afcc5d",
                0,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="2",
                theme_title="Векторы и операции с ними",
                theme_order_index=0,
                snapshot_theme_id="64fdf550-dcad-489a-aea5-0682edf81d76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="vector-27663-coordinate-length",
                rewrite_existing_solution=True,
            ),

    _profile(
                "27707",
                "f60e3532-b35b-4da1-abd1-c2a5031c58cd",
                2,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="2",
                theme_title="Векторы и операции с ними",
                theme_order_index=0,
                snapshot_theme_id="64fdf550-dcad-489a-aea5-0682edf81d76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="vector-27707-rectangle-diagonal-length",
                rewrite_existing_solution=True,
                condition_asset_id="e1e8a146-f2d6-49fe-aa8a-c2761f0a55ec",
                condition_asset_sha256=(
                    "de1cdff1c2f575f321d102862981e501"
                    "0b54b6b1313bc9bae15cd06f80d182f0"
                ),
            ),

    _profile(
                "27708",
                "363c95ed-4a3d-421e-a382-240b162aa85b",
                3,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="2",
                theme_title="Векторы и операции с ними",
                theme_order_index=0,
                snapshot_theme_id="64fdf550-dcad-489a-aea5-0682edf81d76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="vector-27708-rectangle-vector-sum-length",
                rewrite_existing_solution=True,
                condition_asset_id="83e55258-af58-415f-8b8b-0dd18e7c596c",
                condition_asset_sha256=(
                    "b6985c2e9d8332c85a9c97972bd11ff"
                    "6b511619b214b465694d3f42c4bec6e18"
                ),
            ),

    _profile(
                "27718",
                "d50899c8-97e9-4f30-a76c-69f2e919f379",
                13,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="2",
                theme_title="Векторы и операции с ними",
                theme_order_index=0,
                snapshot_theme_id="64fdf550-dcad-489a-aea5-0682edf81d76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="vector-27718-rhombus-diagonal-difference",
                rewrite_existing_solution=True,
                condition_asset_id="04298a22-5a29-4405-bdab-329a35c976f7",
                condition_asset_sha256=(
                    "bbbdee49f44a34050b9a247b3fec3d3"
                    "a0a386c4992c6a11b56b2ef7a3839c83a"
                ),
            ),
)
