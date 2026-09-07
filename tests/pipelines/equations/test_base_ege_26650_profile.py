"""Registration coverage for the base-EGE exponential-equation group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_26650_reuses_common_base_exponential_handler() -> None:
    profile = get_group_profile("ege-base-26650")

    assert profile.source_group_id == "345a3156-5753-4b0b-b3ba-2bf8c4e8681e"
    assert profile.catalog_snapshot_id == "4073fc7b-2056-4697-b18b-38741c94d0f4"
    assert profile.content_rule_key == "exponential-26650-common-base-affine-exponent"
