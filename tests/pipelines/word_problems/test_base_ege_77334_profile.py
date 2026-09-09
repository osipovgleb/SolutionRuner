"""Registration coverage for the base-EGE verbal-arithmetic group 77334."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_77334_registers_the_word_problem_handler() -> None:
    profile = get_group_profile("ege-base-77334")

    assert profile.source_group_id == "9a5b4417-18ad-490c-86cf-53c5fbd70abb"
    assert profile.catalog_snapshot_id == "4073fc7b-2056-4697-b18b-38741c94d0f4"
    assert profile.content_rule_key == "word-problem-77334-currency-purchase-rounding"
