"""Group bindings for this domain; handler implementations live separately."""
from solution_runner.pipelines.core.profile_definitions import (
    _profile,
)

PROFILES = (
    _profile(
                "27591",
                "cba0bfd4-8e64-4d51-812e-0049e9e86e9b",
                0,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="1",
                theme_title="Треугольники общего вида",
                theme_order_index=2,
                snapshot_theme_id="ade013e0-059b-4b5e-bdb4-b4d701c2ca76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="general-triangle-27591-area-sas-30",
            ),

    _profile(
                "561168", "8e613f33-1103-4aef-a8da-3155a43e4e1c", 22,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="1", theme_title="Треугольники общего вида",
                theme_order_index=2, snapshot_theme_id="ade013e0-059b-4b5e-bdb4-b4d701c2ca76",
                expected_vertices=None, strategy_key=None, workflow_kind="content_rule",
                content_rule_key="general-triangle-561168-obtuse-included-angle-area",
                rewrite_existing_solution=True,
            ),

    _profile(
                "681454", "254dd37d-7ec4-40b6-9c5a-6812f32f055f", 23,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="1", theme_title="Треугольники общего вида",
                theme_order_index=2, snapshot_theme_id="ade013e0-059b-4b5e-bdb4-b4d701c2ca76",
                expected_vertices=None, strategy_key=None, workflow_kind="content_rule",
                content_rule_key="general-triangle-681454-bisector-angle",
                rewrite_existing_solution=True,
            ),

    _profile(
                "27752",
                "d79679bf-ed11-4924-bc43-84ff8c2bb900",
                4,
                catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                category_key="1",
                theme_title="Треугольники общего вида",
                theme_order_index=2,
                snapshot_theme_id="ade013e0-059b-4b5e-bdb4-b4d701c2ca76",
                expected_vertices=None,
                strategy_key=None,
                workflow_kind="content_rule",
                content_rule_key="general-triangle-27752-angle-ratio",
                rewrite_existing_solution=True,
                condition_asset_id="74d09078-6b65-4331-ab6f-2b3c7e7dbe84",
                condition_asset_sha256=(
                    "074c1cd588d00ba7fccad7e06e301a5d"
                    "90601b65486d1b9710473666dde1fb93"
                ),
            ),

    *(
                _profile(
                    group_key,
                    source_group_id,
                    order_index,
                    catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                    category_key="1",
                    theme_title="Треугольники общего вида",
                    theme_order_index=2,
                    snapshot_theme_id="ade013e0-059b-4b5e-bdb4-b4d701c2ca76",
                    expected_vertices=None,
                    strategy_key=None,
                    workflow_kind="content_rule",
                    content_rule_key=rule,
                )
                for group_key, source_group_id, order_index, rule in (
                    ("27592", "222a6476-41c9-460e-a8d6-964c7f8e5fdb", 1, "general-triangle-27592-midline-area"),
                    ("27623", "e5f64691-1349-4536-84cd-fd0b96ce573c", 2, "general-triangle-27623-altitude-area-ratio"),
                    ("27743", "2a5de0a0-a8a4-4e62-8bbe-fee17e7cbc5d", 3, "general-triangle-27743-exterior-angle"),
                    ("27757", "5379db65-ac41-44f9-90ef-14841a34b4a6", 5, "general-triangle-27757-altitude-angle"),
                    ("27758", "e34ccc5c-e73b-476e-8853-200aef746fe2", 6, "general-triangle-27758-bisector-angle"),
                    ("27759", "3b5e0e36-0f29-4a67-911f-e9de436f9847", 7, "general-triangle-27759-bisector-exterior-angle"),
                    ("27762", "09f4d8bb-5a05-4064-a238-e41fa27be7dc", 8, "general-triangle-27762-orthocenter-angle"),
                    ("27763", "da77c136-d3c9-449d-b553-efe38e7237b0", 9, "general-triangle-27763-altitudes-angle-sum"),
                    ("27764", "ace78318-f34b-4458-9cc5-de9d60c6a627", 10, "general-triangle-27764-incenter-angle"),
                    ("27767", "0935a9b9-df78-45ae-8d59-a05a5620032b", 11, "general-triangle-27767-altitude-bisector-intersection"),
                    ("27768", "5c4b77d7-1161-4791-a4f1-fba3a25caf1a", 12, "general-triangle-27768-bisector-equal-segments-angle"),
                    ("27769", "ae798923-fe8c-4e80-ad15-d186ba3c3e27", 13, "general-triangle-27769-extension-isosceles-angle"),
                    ("27776", "a6a80898-a164-4477-9b42-198c3f53d071", 14, "general-triangle-27776-bisector-congruent-angle"),
                    ("27777", "468da972-47cf-4932-b5d4-caa90170ba66", 15, "general-triangle-27777-exterior-bisector-isosceles-angle"),
                    ("27778", "a61797fc-3586-4a7c-ba12-224df14b1006", 16, "general-triangle-27778-incenter-bisectors-angle"),
                    ("27779", "274522b6-334a-4be7-a172-5380a38dfc30", 17, "general-triangle-27779-orthocenter-altitudes-angle"),
                    ("317337", "419acdb9-9d6a-4b74-8b95-1ac888864fd4", 18, "general-triangle-317337-midline-small-area-to-total"),
                    ("319058", "5784d6be-e15e-4702-9f14-3366852d30ae", 19, "general-triangle-319058-midline-trapezoid-area"),
                    ("500142", "fe1d0484-1d3d-43d8-b749-09afd351efac", 20, "general-triangle-500142-altitudes-obtuse-angle"),
                    ("510796", "9da66d84-8afa-49c3-af98-d709b67b0ff6", 21, "general-triangle-510796-extended-altitudes-angle"),
                )
            ),
)
