"""Registration coverage for the base-EGE equal-squares group."""

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.equations.group_77368_planner import build_repair_plan


def test_base_ege_group_77368_reuses_the_equal_squares_handler() -> None:
    profile = get_group_profile("ege-base-77368")

    assert profile.source_group_id == "909e4f1b-ce9e-4ef0-b5fb-f46b93852755"
    assert (
        profile.content_rule_key
        == "elementary-equations-77368-equal-squares-first-solution"
    )


@pytest.mark.parametrize(
    "formula", [r"(2x+7)^{2}=(2x+7)^{2}", r"(3x+1)^{2}=(3x+3)^{2}"]
)
def test_nonunique_or_nonterminating_equal_square_roots_fail_closed(formula):
    context = {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "html": f'<p><span data-inline-latex="{formula}"></span></p>',
                }
            ],
        }
    }
    with pytest.raises(ValueError):
        build_repair_plan(context, parent_condition_asset_id=None)
