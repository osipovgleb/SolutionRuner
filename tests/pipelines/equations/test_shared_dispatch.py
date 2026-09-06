from solution_runner.launcher import main
from solution_runner.pipelines.grid_polygon.launcher import main as shared_main
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.runtime import (
    _build_content_plan, _planner_constraints, _requires_parent_condition_asset,
)


def test_equation_handler_uses_shared_launcher_and_dispatch():
    assert main is shared_main
    profile = get_group_profile('26656')
    assert _planner_constraints(profile.content_rule_key) == {}
    assert not _requires_parent_condition_asset(profile.content_rule_key)
    context = {'normalized_content': {
        'format': 'teacherhelper-normalized', 'schema_version': 3,
        'assets': [], 'sections': [{
            'key': 'condition', 'asset_keys': [],
            'html': '<p>Найдите корень уравнения <span data-inline-latex="\\sqrt{30-7x}=4"></span>.</p>',
        }],
    }}
    plan = _build_content_plan(context, parent_asset_id=None,
                               content_rule_key=profile.content_rule_key)
    assert plan.answer == '2'
    assert len(plan.transformations) == 2
