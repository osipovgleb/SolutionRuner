"""Registration coverage for the base-EGE equal-squares group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_77368_reuses_the_equal_squares_handler() -> None:
    profile = get_group_profile("ege-base-77368")

    assert profile.source_group_id == "909e4f1b-ce9e-4ef0-b5fb-f46b93852755"
    assert profile.content_rule_key == "elementary-equations-77368-equal-squares-first-solution"
