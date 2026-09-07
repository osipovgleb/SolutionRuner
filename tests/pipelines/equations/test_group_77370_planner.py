"""Registration coverage for the base-EGE expanded-square group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_77370_reuses_the_expanded_square_handler() -> None:
    profile = get_group_profile("ege-base-77370")

    assert profile.source_group_id == "eb342ca5-a2b5-431f-a17f-149b6a5594c9"
    assert profile.content_rule_key == "elementary-equations-77370-expanded-square-linear"
