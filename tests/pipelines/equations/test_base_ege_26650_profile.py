"""Registration coverage for the base-EGE exponential-equation group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_26650_reuses_common_base_exponential_handler() -> None:
    profile = get_group_profile("ege-base-26650")

    assert profile.source_group_id == "345a3156-5753-4b0b-b3ba-2bf8c4e8681e"
    assert profile.catalog_snapshot_id == "4073fc7b-2056-4697-b18b-38741c94d0f4"
    assert profile.content_rule_key == "exponential-26650-common-base-affine-exponent"


def test_base_ege_group_26651_reuses_common_base_exponential_handler() -> None:
    profile = get_group_profile("ege-base-26651")

    assert profile.source_group_id == "632e99b6-b459-4014-9107-a08ea7671a13"
    assert profile.content_rule_key == "exponential-26650-common-base-affine-exponent"


def test_base_ege_group_26652_reuses_common_base_exponential_handler() -> None:
    profile = get_group_profile("ege-base-26652")

    assert profile.source_group_id == "b8a581c1-2306-4e40-968d-7ef34be545f9"
    assert profile.content_rule_key == "exponential-26650-common-base-affine-exponent"


def test_remaining_base_ege_common_base_exponential_groups_are_registered() -> None:
    expected = {
        "ege-base-26653": "482bd116-419d-40ac-9944-6af2ce063696",
        "ege-base-26654": "42a11129-6963-4d6a-9845-5448464c786d",
        "ege-base-26655": "5cb6590f-4f55-4ba0-a1b7-d7a032e6e826",
        "ege-base-26666": "d005f6cf-71db-4a3b-a139-c221f0e66076",
        "ege-base-26670": "015365bd-c516-4da9-b2b6-d7a4085ec0bc",
        "ege-base-513732": "90930c35-7fdd-4cc4-83f0-0eca305aad91",
        "ege-base-513814": "6b15326a-b48f-4719-8d08-46e48c2a255c",
        "ege-base-520555": "9ef31e95-eac3-4e3b-afcc-bd13d83ca20e",
        "ege-base-520575": "b341db9d-51ac-42e4-be64-3b1d18d6fca2",
        "ege-base-520615": "a23b2a5d-0d22-402f-8da6-1b32bc0edc36",
        "ege-base-522355": "915b4a2f-1c7e-4d9f-9dc0-df28404d8b63",
        "ege-base-522674": "215bb8f7-a80c-4d27-a325-98001074c47e",
        "ege-base-536849": "a9711b31-bc19-4476-bd6c-d610372c34de",
    }

    for group_key, source_group_id in expected.items():
        profile = get_group_profile(group_key)
        assert profile.source_group_id == source_group_id
        assert profile.content_rule_key == "exponential-26650-common-base-affine-exponent"
