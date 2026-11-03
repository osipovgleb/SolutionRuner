"""Public preparation of all reviewed two-ray angle families without side effects."""

from ...core.errors import ContentPlanError
from ...core.numbers import format_answer
from ...probability import solution_diagrams as diagrams
from .altitude_parent import _source
from .basic_parent import _targeted
from .construction_angles import RULES, SOURCES, read_context
from .construction_ray_figures import prepare_figure
from .construction_ray_proofs import render, review_parent
from .construction_svg import SOURCE_HASHES


def prepare(
    context,
    *,
    parent_asset_id,
    parent_solution_html,
    content_rule_key,
    generated_solution_assets=(),
):
    from .planner import RepairPlan, _section

    review_parent(parent_solution_html, content_rule_key)
    expected_pair = RULES[content_rule_key][0]
    if parent_asset_id != SOURCES[expected_pair]:
        raise ContentPlanError("the reviewed parent construction figure is required")
    _source(parent_asset_id, sources=SOURCE_HASHES)
    model = read_context(context).require_rule(content_rule_key)
    content = context["normalized_content"]
    condition = _section(content, "condition")
    changes = prepare_figure(content, condition, model, generated_solution_assets)
    answer = format_answer(model.answer)
    plan = diagrams.repair(
        condition,
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        answer,
        render(model),
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
