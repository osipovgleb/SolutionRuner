"""Profile bindings for exam inequalities."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .exponential_inequality_groups import GROUPS as EXPONENTIAL_INEQUALITY_GROUPS
from .logarithmic_inequality_groups import GROUPS as LOGARITHMIC_INEQUALITY_GROUPS
from .rational_inequality_figures import GROUPS as RATIONAL_INEQUALITY_GROUPS

PROFILES = tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title=theme,
        theme_order_index=theme_index,
        snapshot_theme_id=theme_id,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, group_id, index, theme, theme_index, theme_id, rule in (
        tuple(
            (*row[:6], "exam-rational-inequality-" + row[6].replace("_", "-"))
            for row in RATIONAL_INEQUALITY_GROUPS
        )
        + EXPONENTIAL_INEQUALITY_GROUPS
        + LOGARITHMIC_INEQUALITY_GROUPS
    )
)

PROFILES += (
    _profile(
        "507612",
        "85241762-9501-4cea-9e8e-86e159f08539",
        1,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства, содержащие радикалы",
        theme_order_index=0,
        snapshot_theme_id="70deb136-d138-41a5-a386-adad31cf126b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-radical-inequality-three-root",
        rewrite_existing_solution=True,
    ),
)

PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства, содержащие радикалы",
        theme_order_index=0,
        snapshot_theme_id="70deb136-d138-41a5-a386-adad31cf126b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-radical-inequality-" + method.replace("_", "-"),
        rewrite_existing_solution=True,
    )
    for key, group_id, index, method in (
        ("507582", "31f0909a-e0b7-48a9-ad15-e9579497fb62", 0, "squared_quotient"),
        ("485951", "247cd949-d3db-4e5a-b106-278b47937f0a", 6, "root_factor"),
        ("507175", "c2eb68b3-2224-4ff5-b72d-95d82ab54619", 7, "even_power"),
        ("507894", "b15c2ff9-0a2c-43f4-9462-10c2c47a0c43", 3, "difference"),
    )
)

PROFILES += (
    _profile(
        "508540",
        "f40101b1-caa2-4be4-8ccb-8ba4bfe663bb",
        1,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Показательные выражения и иррациональности",
        theme_order_index=9,
        snapshot_theme_id="3e483559-e0a8-4041-93a6-b45a9dd56746",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-radical-comparison",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "507795",
        "8d7f9c9a-300e-4cd0-842c-bd4cdf573acd",
        0,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Показательные выражения и иррациональности",
        theme_order_index=9,
        snapshot_theme_id="3e483559-e0a8-4041-93a6-b45a9dd56746",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-radical-product",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "507503",
        "f62344dd-0119-4e49-8317-3d61956b3422",
        1,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и показательные выражения",
        theme_order_index=10,
        snapshot_theme_id="d77d13af-fea6-4a1c-b7b5-310900de07e5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-exponential-quadratic",
        rewrite_existing_solution=True,
    ),
)

PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и показательные выражения",
        theme_order_index=10,
        snapshot_theme_id="d77d13af-fea6-4a1c-b7b5-310900de07e5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithmic-power-" + method.replace("_", "-"),
        rewrite_existing_solution=True,
    )
    for key, group_id, index, method in (
        ("508458", "d02247b2-ab1c-4ad6-a8fb-673e670304a0", 5, "linear_reciprocity"),
        ("508471", "baf09951-bac8-4ea6-b32c-917789cef0d9", 7, "square_coordinate"),
    )
)

PROFILES += (
    _profile(
        "562040",
        "ab71fa47-c7ae-4ba1-beae-89bd35cc3519",
        28,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и показательные выражения",
        theme_order_index=10,
        snapshot_theme_id="d77d13af-fea6-4a1c-b7b5-310900de07e5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-log-product",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "507779",
        "5f4aa271-8b58-4bb1-ad75-a6a1aa5d284c",
        0,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и иррациональности",
        theme_order_index=11,
        snapshot_theme_id="984922a1-4e2e-4f11-9c0e-b1f2fda35988",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-radical-quotient",
        rewrite_existing_solution=True,
    ),
)

PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с модулем",
        theme_order_index=13,
        snapshot_theme_id="b48e5469-1b51-468f-b2fc-e350057f890d",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-absolute-inequality-" + method.replace("_", "-"),
        rewrite_existing_solution=True,
    )
    for key, group_id, index, method in (
        ("507667", "bf103279-f28c-4373-bf4e-f2e85c605b94", 0, "squared_quotient"),
        ("508405", "883a3a0f-0152-4a25-be66-1400b81316fe", 2, "affine_substitution"),
    )
)

PROFILES += (
    _profile(
        "508433",
        "eff3a53f-6add-41f6-b7b1-dace94ea5794",
        6,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с модулем",
        theme_order_index=13,
        snapshot_theme_id="b48e5469-1b51-468f-b2fc-e350057f890d",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-absolute-inequality-quadratic-comparison",
        rewrite_existing_solution=True,
    ),
)

PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с модулем",
        theme_order_index=13,
        snapshot_theme_id="b48e5469-1b51-468f-b2fc-e350057f890d",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-absolute-power-" + method.replace("_", "-"),
        rewrite_existing_solution=True,
    )
    for key, group_id, index, method in (
        ("508567", "055a4d51-b68d-4264-8909-6549c5cf1794", 9, "reciprocal"),
        ("560732", "4cd11b9b-2b5c-40e5-a27c-fe179ccafdd6", 16, "signed_exponent"),
    )
)

PROFILES += (
    _profile(
        "484588",
        "ce1dcde5-8aa9-403c-97c1-6b9c3ced2676",
        2,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Другие неравенства смешанного типа",
        theme_order_index=14,
        snapshot_theme_id="fa84ece5-aae6-49e3-8024-71ffe8310355",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-log-upper-bound",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "507691",
        "855be483-863e-41b5-ba28-5fa2f60f174f",
        0,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Другие неравенства смешанного типа",
        theme_order_index=14,
        snapshot_theme_id="fa84ece5-aae6-49e3-8024-71ffe8310355",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-absolute-fraction",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "519640",
        "e3b42070-433b-4220-ae6f-d8db469f7867",
        5,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Другие неравенства смешанного типа",
        theme_order_index=14,
        snapshot_theme_id="fa84ece5-aae6-49e3-8024-71ffe8310355",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-absolute-log-power-identity",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "513429",
        "bfa4238b-5ed4-4a14-a87e-a1826e1323d5",
        12,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и показательные выражения",
        theme_order_index=10,
        snapshot_theme_id="d77d13af-fea6-4a1c-b7b5-310900de07e5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-monotonic-range",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "484579",
        "b05b863d-377d-483e-95c2-8eedcce8a664",
        0,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Логарифмы и показательные выражения",
        theme_order_index=10,
        snapshot_theme_id="d77d13af-fea6-4a1c-b7b5-310900de07e5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-factored-power-domain",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "520497",
        "1d53ffbf-4773-4801-9911-095891efe9f2",
        31,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с логарифмами по переменному основанию",
        theme_order_index=6,
        snapshot_theme_id="31924b26-1eb2-4fa9-be31-0a36f5ee7e54",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-polynomial-logarithm-base-cases",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "508392",
        "6b13aa63-8619-4392-b9fb-6cc5d4a48068",
        4,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с логарифмами по переменному основанию",
        theme_order_index=6,
        snapshot_theme_id="31924b26-1eb2-4fa9-be31-0a36f5ee7e54",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-reciprocal-square-methods",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "508488",
        "321e40dd-671c-41e3-a75d-f9918770d3e2",
        4,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с логарифмами по переменному основанию, применение рационализации",
        theme_order_index=7,
        snapshot_theme_id="ff7e4f27-be00-4a6b-b95a-b5a0a9b2c03b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-single-logarithm-three-methods",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "508513",
        "49f76027-8d6b-4a50-aadb-144cf1a1787f",
        6,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с логарифмами по переменному основанию, применение рационализации",
        theme_order_index=7,
        snapshot_theme_id="ff7e4f27-be00-4a6b-b95a-b5a0a9b2c03b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-base-power-cancellation",
        rewrite_existing_solution=True,
    ),
)

PROFILES += (
    _profile(
        "507893",
        "d4cf4121-75f3-47dd-b327-549c85af7553",
        3,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="16",
        theme_title="Неравенства с логарифмами по переменному основанию",
        theme_order_index=6,
        snapshot_theme_id="31924b26-1eb2-4fa9-be31-0a36f5ee7e54",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithm-rational-base-cases",
        rewrite_existing_solution=True,
    ),
)
