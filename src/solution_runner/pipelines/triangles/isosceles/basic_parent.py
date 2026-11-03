"""Prepare six base/side families through their reviewed shared parent methods."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.altitude_solver import AltitudeSolveError
from ..right.basic_parent import _targeted
from .basic_figures import BARE, HEIGHT, source_bytes
from .basic_figures import prepare as prepare_figures
from .basic_model import read_context
from .basic_proofs import render, review_parent
from .planner import IsoscelesTrianglePlanError, RepairPlan, _section


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    try:
        review_parent(parent_solution_html, content_rule_key)
        model = read_context(context).require_rule(content_rule_key)
        separate = (model.function, model.given_kind) == ("tg", "base")
        if parent_condition_asset_id != (BARE if separate else HEIGHT):
            raise ContentPlanError("the reviewed parent condition figure is required")
        source_bytes(parent_condition_asset_id)
        if separate:
            if (
                len(parent_solution_assets) != 1
                or parent_solution_assets[0].get("asset_key") != "image_2"
                or parent_solution_assets[0].get("source_asset_id") != HEIGHT
                or parent_solution_assets[0].get("url") != "/assets/" + HEIGHT
            ):
                raise ContentPlanError(
                    "the reviewed separate parent height figure is required"
                )
        elif parent_solution_assets:
            raise ContentPlanError("the single-figure parent has no solution image")
        content = context["normalized_content"]
        condition = _section(content, "condition")
        changes, figure_html, keys = prepare_figures(
            context, condition, generated_solution_assets
        )
        answer = exact_answer(model.answer)
        plan = diagrams.repair(
            condition,
            _targeted(_section(content, "answer")),
            _targeted(_section(content, "solution")),
            answer,
            render(model, figure_html=figure_html),
            keys=keys,
            asset_changes=changes,
        )
        return RepairPlan(plan.answer, plan.transformations)
    except (AltitudeSolveError, IsoscelesTrianglePlanError) as exc:
        raise ContentPlanError(str(exc)) from exc
