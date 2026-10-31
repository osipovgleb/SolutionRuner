"""Source-group registrations for deterministic verbal arithmetic runners."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .profile_families import PROFILE_FAMILIES

PROFILES = (
    _profile(
        "77331",
        "f23ffe4f-acd2-4f14-966e-fbb336468960",
        4,
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        category_key="1",
        theme_title="Разные задачи",
        theme_order_index=0,
        snapshot_theme_id="0be411f6-d020-4856-a938-df5d2b2addf4",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-problem-77331-mobile-call-duration",
    ),
    _profile(
        "26623",
        "d269a4c3-2ae2-4255-a993-f69533b50a4e",
        0,
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        category_key="1",
        theme_title="Разные задачи",
        theme_order_index=0,
        snapshot_theme_id="0be411f6-d020-4856-a938-df5d2b2addf4",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-problem-26623-monthly-travel-pass-savings",
    ),
    _profile(
        "ege-base-77334",
        "9a5b4417-18ad-490c-86cf-53c5fbd70abb",
        0,
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        category_key="1",
        theme_title="Округление с недостатком",
        theme_order_index=0,
        snapshot_theme_id="7591db40-9887-4dd9-b8b9-49877194edb8",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-problem-77334-currency-purchase-rounding",
    ),
    *(
        _profile(
            group_key,
            source_group_id,
            order_index,
            catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
            category_key="1",
            theme_title="Округление с недостатком",
            theme_order_index=0,
            snapshot_theme_id="7591db40-9887-4dd9-b8b9-49877194edb8",
            expected_vertices=None,
            strategy_key=None,
            workflow_kind="content_rule",
            content_rule_key=rule_key,
        )
        for group_key, source_group_id, order_index, rule_key in (
            (
                "ege-base-506389",
                "9a8d923b-f85f-438b-a85b-db45267ef5be",
                3,
                "word-problem-506389-whole-item-purchase",
            ),
            (
                "ege-base-26626",
                "2f2a64b4-a6c2-47f3-b13b-f5412e5771aa",
                4,
                "word-problem-26626-bundle-promotion",
            ),
            (
                "ege-base-26637",
                "028ce7ac-868d-48bc-a3f6-db199a33fb28",
                5,
                "word-problem-26637-odd-bouquet",
            ),
            (
                "ege-base-26641",
                "43c9216a-e8fe-4bd2-b4d6-75a5680e75df",
                6,
                "word-problem-26641-full-bookcases",
            ),
        )
    ),
    _profile(
        "ege-base-26624",
        "7128d020-5ab0-4b5d-82fa-5c6e0a7e0ec0",
        0,
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        category_key="1",
        theme_title="Округление с избытком",
        theme_order_index=1,
        snapshot_theme_id="3df4b09b-b657-4b1c-8d16-21d82120befc",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-problem-26624-medicine-course-ceiling",
    ),
    _profile(
        "323514",
        "55f96aae-f624-43de-b6d4-25f0c6601752",
        4,
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        category_key="1",
        theme_title="Округление с избытком",
        theme_order_index=1,
        snapshot_theme_id="3df4b09b-b657-4b1c-8d16-21d82120befc",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-problem-323514-wallpaper-rolls-ceiling",
    ),
    *(
        _profile(
            key,
            source_id,
            index,
            catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
            category_key="11",
            theme_title="Задачи на проценты, сплавы и смеси",
            theme_order_index=0,
            snapshot_theme_id="c6467e7e-a271-4928-819a-ab0ba2a62b1d",
            expected_vertices=None,
            strategy_key=None,
            workflow_kind="content_rule",
            content_rule_key=rule,
            rewrite_existing_solution=rewrite,
        )
        for key, source_id, index, rule, rewrite in (
            (
                "ege-profile-99565",
                "0161fad7-7b9c-446c-a2f1-5fefce5f5acf",
                0,
                "word-problem-99565-successive-population-change",
                False,
            ),
            (
                "ege-profile-99566",
                "63d84341-4b56-490a-8340-1769dddc98e8",
                1,
                "word-problem-99566-equal-rise-fall-percent",
                True,
            ),
            (
                "ege-profile-99567",
                "1524e7cf-3c23-401b-8a88-b3c50adcf89c",
                2,
                "word-problem-99567-shirt-jacket-percent",
                True,
            ),
            (
                "ege-profile-99568",
                "cf7d2aaa-c45c-414a-9c3b-3d8a814769cf",
                3,
                "word-problem-99568-family-income-system",
                True,
            ),
            (
                "ege-profile-99569",
                "52572cf4-73c7-43a6-ae9b-299ae8a7bca4",
                4,
                "word-problem-99569-refrigerator-price-decline",
                True,
            ),
            (
                "ege-profile-99570",
                "681eb28d-37f8-4cdb-adb2-718a91c8d754",
                5,
                "word-problem-99570-company-capital-profit-tables",
                True,
            ),
        )
    ),
)


PROFILES += tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="11",
        theme_title="Задачи на проценты, сплавы и смеси",
        theme_order_index=0,
        snapshot_theme_id="c6467e7e-a271-4928-819a-ab0ba2a62b1d",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, source_id, order, rule in (
        ("99571", "bc264726-49be-481d-94cd-8c986dd56ac4", 6, "word-mixture-balance"),
        ("99572", "6de05d46-0d46-4c74-8deb-8bc0cb1e2c41", 7, "word-mixture-balance"),
        ("99573", "29997c83-f25f-4a66-8df0-058b2b369c0f", 8, "word-mixture-balance"),
        ("99574", "8fe7a1f1-58b5-4ca6-a665-0514d7e3831c", 9, "word-mixture-balance"),
        ("99575", "3d9adf6c-c761-4d2d-bec4-2e78a2e26790", 10, "word-mixture-balance"),
        ("99576", "0b994479-942b-456c-854f-a5e97f8ef82d", 11, "word-mixture-balance"),
        ("99577", "ae2ac450-2c70-4c32-b267-8de1c7dbbb7b", 12, "word-mixture-balance"),
        ("99578", "3bf6b2ab-5f99-41f1-a7e7-b5003d17df0c", 13, "word-mixture-balance"),
        ("323855", "cabb643d-5a8a-4979-b5e1-053b7a469dae", 14, "word-compound-deposit"),
        ("639947", "24753e98-7cc3-4cc8-b12f-ac90e213654a", 15, "word-mixture-balance"),
        ("676853", "52f27c57-e9d0-4d08-b32a-55e3fd0e6fa6", 16, "word-mixture-balance"),
    )
)


PROFILES += tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="11",
        theme_title=theme_title,
        theme_order_index=theme_order,
        snapshot_theme_id=theme_id,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for theme_title, theme_id, theme_order, families in PROFILE_FAMILIES
    for rule, members in families
    for key, source_id, order in members
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="13",
        theme_title="Вклады",
        theme_order_index=0,
        snapshot_theme_id="6cbc7919-2d53-4d47-9103-6d9636aca9b3",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-compound-deposit",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("704682", "14f40986-c372-42ff-99e5-3beb8aeb1de5", 0),
        ("704683", "8b9c0395-9820-49fe-b11e-8f5f9ccde0b7", 1),
        ("704684", "96e7c409-e211-4f2e-ba3e-f5fa2ecd8e75", 2),
        ("704685", "7dbd8687-b96e-48e3-bc34-690b941c2d1e", 3),
        ("704686", "4a92d288-066f-4ca9-9120-3d7b3be2fb37", 4),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="13",
        theme_title="Кредиты",
        theme_order_index=1,
        snapshot_theme_id="87e2a62d-a8cc-4bcb-b02e-3a05b81c2519",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="word-differentiated-credit",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("517203", "fe9f8bcd-9661-462a-99db-dce206c6a464", 1),
        ("517480", "9f46abb3-e04c-4753-ab3c-6dcc8aa423d7", 2),
        ("517569", "c58722c2-5feb-42f3-b6a1-52dd2b5841a0", 4),
    )
)
