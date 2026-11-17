"""Group bindings; catalog prefixes disambiguate reused source task numbers."""

from solution_runner.pipelines.core.profile_definitions import (
    _profile,
)

from .base_expression_profiles import PROFILES as _BASE_EXPRESSION_PROFILES
from .exam_elementary_profiles import PROFILES as _EXAM_ELEMENTARY_PROFILES
from .exam_inequality_profiles import PROFILES as EXAM_INEQUALITY_PROFILES
from .exam_mixed_trigonometric_profiles import (
    PROFILES as _EXAM_MIXED_TRIGONOMETRIC_PROFILES,
)
from .exam_trigonometric_factor_profiles import (
    PROFILES as _EXAM_TRIGONOMETRIC_FACTOR_PROFILES,
)
from .exam_trigonometric_selection_profiles import (
    PROFILES as _EXAM_TRIGONOMETRIC_SELECTION_PROFILES,
)
from .numeric_expression_profiles import PROFILES as _NUMERIC_EXPRESSION_PROFILES

PROFILES = _BASE_EXPRESSION_PROFILES

PROFILES += (
    _profile(
        "689090",
        "72c3f0ef-de74-4fde-8f9d-0f3edfe8dc14",
        8,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Рациональные уравнения",
        theme_order_index=1,
        snapshot_theme_id="ff83f99f-e437-4bc1-a0d3-a78223deab73",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="elementary-equations-315119-equal-unit-fractions",
        rewrite_existing_solution=True,
    ),
    _profile(
        "639943",
        "5d16a900-5dc1-4f0f-82a7-aae97ddf40ff",
        13,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Логарифмические уравнения",
        theme_order_index=4,
        snapshot_theme_id="dc2e142c-980d-4e7d-81d8-4ca5664b2b0b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="logarithm-common-normalized",
        rewrite_existing_solution=True,
    ),
    _profile(
        "509413",
        "490f323f-4e73-41eb-be5c-aee09e6a6310",
        11,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Показательные уравнения",
        theme_order_index=3,
        snapshot_theme_id="9c4caca6-2ff6-4256-8ad2-a0caca504211",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exponential-26650-common-base-affine-exponent",
        rewrite_existing_solution=True,
    ),
    _profile(
        "672744",
        "ab2fac89-3623-4c4a-b9ec-3dac31d47dfb",
        12,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Показательные уравнения",
        theme_order_index=3,
        snapshot_theme_id="9c4caca6-2ff6-4256-8ad2-a0caca504211",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exponential-26650-common-base-affine-exponent",
        rewrite_existing_solution=True,
    ),
    _profile(
        "676849",
        "dfe9a902-b059-4286-8d6b-fc0428929e50",
        13,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Показательные уравнения",
        theme_order_index=3,
        snapshot_theme_id="9c4caca6-2ff6-4256-8ad2-a0caca504211",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exponential-26650-common-base-affine-exponent",
        rewrite_existing_solution=True,
    ),
    _profile(
        "704177",
        "21bed103-35e7-4372-ac78-07b7f576eb81",
        14,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Показательные уравнения",
        theme_order_index=3,
        snapshot_theme_id="9c4caca6-2ff6-4256-8ad2-a0caca504211",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exponential-26650-common-base-affine-exponent",
        rewrite_existing_solution=True,
    ),
    _profile(
        "77375",
        "0c50c4c6-4d1b-40f5-a6b5-08b05021bc26",
        8,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-26668-square-root-negative-x",
        rewrite_existing_solution=True,
    ),
    _profile(
        "628738",
        "7931d8ab-15f3-4b93-8eff-ea645aa83853",
        13,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-26668-square-root-negative-x",
        rewrite_existing_solution=True,
    ),
    _profile(
        "525399",
        "5f56c1ae-3d0a-486d-a632-4826a3c54dcf",
        12,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Логарифмические уравнения",
        theme_order_index=4,
        snapshot_theme_id="dc2e142c-980d-4e7d-81d8-4ca5664b2b0b",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="logarithm-77382-affine-base-perfect-power",
        rewrite_existing_solution=True,
    ),
    _profile(
        "504406",
        "5bc5344d-95f3-4931-a2b1-0006238f456a",
        6,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Рациональные уравнения",
        theme_order_index=1,
        snapshot_theme_id="ff83f99f-e437-4bc1-a0d3-a78223deab73",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="elementary-equations-77383-reciprocal-linear",
        rewrite_existing_solution=True,
    ),
    _profile(
        "504427",
        "07e971f4-10d3-4ccd-b23e-4d734229182c",
        7,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Рациональные уравнения",
        theme_order_index=1,
        snapshot_theme_id="ff83f99f-e437-4bc1-a0d3-a78223deab73",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="elementary-equations-77383-reciprocal-linear",
        rewrite_existing_solution=True,
    ),
    _profile(
        "500032",
        "37bad3ac-5dfa-4085-8a9f-dbd13cc9d296",
        9,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-26656-square-root-affine",
        rewrite_existing_solution=True,
    ),
    _profile(
        "501034",
        "2fe7c2b0-bc95-490f-a9dd-aa7335438ce2",
        10,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-26656-square-root-affine",
        rewrite_existing_solution=True,
    ),
    _profile(
        "501205",
        "6d336182-550b-409f-88b2-9c8dc24e6f73",
        11,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-27466-odd-root-affine",
        rewrite_existing_solution=True,
    ),
    _profile(
        "510328",
        "b1e8bb49-9e0c-42de-9738-f684f42bae35",
        12,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="7",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="irrational-26660-square-root-rational-affine",
        rewrite_existing_solution=True,
    ),
)

# Audited OGE inequality-system groups; preserve all editorial solutions.
PROFILES += tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="fd733f80-43d2-4b4a-b903-2423796cbee5",
        category_key="13",
        theme_title="Системы неравенств",
        theme_order_index=0,
        snapshot_theme_id="29856936-1cd0-4f14-94b9-b0bf595395bd",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="inequality-systems-linear-complete",
        rewrite_existing_solution=True,
    )
    for order, (key, source_id) in enumerate(
        (
            ("311672", "89380b0c-acef-48e8-a74b-2a283372bd3d"),
            ("333109", "974f9bf8-c7db-4ac5-b94d-ec7d00b87abd"),
            ("341322", "59cbcb9a-c08c-4d29-8a7d-dabecdaacbb5"),
            ("348461", "9e682f8d-c17d-4ce8-9d7a-37af7159dba9"),
        )
    )
)


# Audited single-quadratic choices in the same OGE theme as group 185.
PROFILES += tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="fd733f80-43d2-4b4a-b903-2423796cbee5",
        category_key="13",
        theme_title="Квадратные неравенства",
        theme_order_index=1,
        snapshot_theme_id="760bb497-c0ac-4833-b37e-aea079eb9af0",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="quadratic-single-interval-choices",
        rewrite_existing_solution=True,
    )
    for order, (key, source_id) in enumerate(
        (
            ("311309", "db140fe5-bb41-4235-ac6a-31c464ade9ed"),
            ("311310", "f7cf8a60-1ee4-4b63-859f-6a780b90de31"),
            ("311311", "d92efd64-7e18-40d1-bd5f-2d6ca2121ef9"),
            ("311385", "cf3000db-56cd-4e87-bd07-0c27e0403413"),
            ("311751", "ca38a142-fc46-4794-889a-1ab74c687973"),
            ("311781", "101353af-121c-416a-add0-7facbb434d3c"),
            ("338497", "93785c1d-a4f8-4c1d-9915-1068180779f7"),
            ("338499", "1cf02c85-5cd5-47b0-9cda-11715bf60325"),
            ("338550", "019da04d-0b7d-44a9-98b7-457b92ff761c"),
            ("349532", "ecc96899-2c3e-4bed-8cf1-e8114116103f"),
            ("350216", "6238e4a0-1f70-4435-98b4-84135b7e70e6"),
            ("352247", "05f0cf10-a029-422c-b841-8b4badaa17e3"),
            ("369736", "9b458809-2776-4b87-a5ed-da37e04a6922"),
            ("471238", "025268dc-a87b-4610-9980-5afe36d31db0"),
        ),
        start=1,
    )
)

# Positive power expression groups.
PROFILES += _NUMERIC_EXPRESSION_PROFILES


PROFILES += _EXAM_ELEMENTARY_PROFILES


PROFILES += _EXAM_TRIGONOMETRIC_FACTOR_PROFILES


PROFILES += _EXAM_TRIGONOMETRIC_SELECTION_PROFILES


PROFILES += _EXAM_MIXED_TRIGONOMETRIC_PROFILES


PROFILES += EXAM_INEQUALITY_PROFILES
