"""Registration coverage for known base-EGE logarithmic groups."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_common_logarithm_groups_reuse_the_existing_handler() -> None:
    expected = {
        "ege-base-26646": "1a0e639a-9539-448f-ad6c-6c50a9fbe36a",
        "ege-base-26647": "b9bff6ae-ca4c-4faa-8471-0f362b161290",
        "ege-base-26648": "306be2a7-8942-4eab-ba0e-a1fb43c24248",
        "ege-base-26649": "ba96dc15-26ce-4ee7-9ae2-383fd1107f63",
        "ege-base-26657": "61068c42-4461-4aa1-b133-4522b6303e0a",
        "ege-base-26659": "4cc7178b-c4a8-4e38-bbb2-a2bdd534d0c3",
    }

    for group_key, source_group_id in expected.items():
        profile = get_group_profile(group_key)
        assert profile.source_group_id == source_group_id
        assert profile.catalog_snapshot_id == "4073fc7b-2056-4697-b18b-38741c94d0f4"
        assert profile.content_rule_key == "logarithm-common-normalized"


def test_base_ege_group_77381_reuses_the_shifted_logarithm_handler() -> None:
    profile = get_group_profile("ege-base-77381")

    assert profile.source_group_id == "f0ff20d8-fa88-48fd-96eb-4279fc046279"
    assert profile.content_rule_key == "logarithm-77381-shifted-equal-logs"
