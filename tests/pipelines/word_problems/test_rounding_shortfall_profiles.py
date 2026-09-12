from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_rounding_shortfall_groups_have_separate_registered_rules() -> None:
    expected = {
        "ege-base-506389": ("9a8d923b-f85f-438b-a85b-db45267ef5be", "word-problem-506389-whole-item-purchase"),
        "ege-base-26626": ("2f2a64b4-a6c2-47f3-b13b-f5412e5771aa", "word-problem-26626-bundle-promotion"),
        "ege-base-26637": ("028ce7ac-868d-48bc-a3f6-db199a33fb28", "word-problem-26637-odd-bouquet"),
        "ege-base-26641": ("43c9216a-e8fe-4bd2-b4d6-75a5680e75df", "word-problem-26641-full-bookcases"),
        "ege-base-26624": ("7128d020-5ab0-4b5d-82fa-5c6e0a7e0ec0", "word-problem-26624-medicine-course-ceiling"),
        "323514": ("55f96aae-f624-43de-b6d4-25f0c6601752", "word-problem-323514-wallpaper-rolls-ceiling"),
        "ege-profile-99565": ("0161fad7-7b9c-446c-a2f1-5fefce5f5acf", "word-problem-99565-successive-population-change"),
        "ege-profile-99566": ("63d84341-4b56-490a-8340-1769dddc98e8", "word-problem-99566-equal-rise-fall-percent"),
        "ege-profile-99569": ("52572cf4-73c7-43a6-ae9b-299ae8a7bca4", "word-problem-99569-refrigerator-price-decline"),
        "ege-profile-99570": ("681eb28d-37f8-4cdb-adb2-718a91c8d754", "word-problem-99570-company-capital-profit-tables"),
    }
    for group_key, (source_group_id, rule_key) in expected.items():
        profile = get_group_profile(group_key)
        assert profile.source_group_id == source_group_id
        assert profile.content_rule_key == rule_key


def test_word_problem_groups_preserve_existing_editorial_solutions() -> None:
    for group_key in (
        "ege-base-77334", "ege-base-506389", "ege-base-26626",
        "ege-base-26637", "ege-base-26641",
        "ege-base-26624",
        "ege-profile-99565",
    ):
        assert get_group_profile(group_key).existing_solution_policy == "preserve"


def test_equal_rise_and_fall_rewrites_solutions_by_explicit_request() -> None:
    assert get_group_profile("ege-profile-99566").existing_solution_policy == "rewrite"


def test_shirt_jacket_group_rewrites_solutions_by_explicit_request() -> None:
    assert get_group_profile("ege-profile-99567").existing_solution_policy == "rewrite"


def test_refrigerator_decline_group_rewrites_solutions_by_explicit_request() -> None:
    assert get_group_profile("ege-profile-99569").existing_solution_policy == "rewrite"
