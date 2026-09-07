"""Registration coverage for the base-EGE completed-square group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_77369_reuses_the_completed_square_handler() -> None:
    profile = get_group_profile("ege-base-77369")

    assert profile.source_group_id == "afee6994-cfb4-4b7e-8dcd-8f017a7e1b50"
    assert profile.content_rule_key == "elementary-equations-77369-completed-square"
