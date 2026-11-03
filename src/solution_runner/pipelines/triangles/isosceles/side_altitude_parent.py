"""Prepare all twelve side-altitude families through one reviewed public handler."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.altitude_solver import AltitudeSolveError
from ..right.basic_parent import _targeted
from .planner import IsoscelesTrianglePlanError, RepairPlan, _section
from .side_altitude_figures import prepare as prepare_figures
from .side_altitude_model import read_context
from .side_altitude_proofs import render, review_parent
from .side_altitude_sources import NOTE_SOURCE, source_bytes

_PARENT_SOURCES = {
    "isosceles-triangle-27320-altitude-from-base-sine": "7882a0e2-3730-4c5a-954d-99b65a800a37",
    "isosceles-triangle-27321-projection-from-base-sine": "9f99e601-0a60-47e7-a20e-934fda25122c",
    "isosceles-triangle-27322-altitude-from-base-cosine": "e646ef3d-a79c-4f92-a916-1e4b976041ca",
    "isosceles-triangle-27323-projection-from-base-cosine": "e646ef3d-a79c-4f92-a916-1e4b976041ca",
    "isosceles-triangle-27324-altitude-from-base-tangent": "e646ef3d-a79c-4f92-a916-1e4b976041ca",
    "isosceles-triangle-27325-projection-from-base-tangent": "2446836d-641d-400e-b4c3-fa09cf977dc3",
    "isosceles-triangle-27326-altitude-from-side-sine": "a41c52d0-9fcc-49cc-ace2-65c676d74aaf",
    "isosceles-triangle-27327-projection-from-side-sine": "a41c52d0-9fcc-49cc-ace2-65c676d74aaf",
    "isosceles-triangle-27328-altitude-from-side-cosine": "a41c52d0-9fcc-49cc-ace2-65c676d74aaf",
    "isosceles-triangle-27329-projection-from-side-cosine": "a41c52d0-9fcc-49cc-ace2-65c676d74aaf",
    "isosceles-triangle-27330-sine-from-altitude-and-base": "45a6fa73-fe2e-4355-8184-d09a848a9e82",
    "isosceles-triangle-27331-cosine-from-altitude-and-base": "e646ef3d-a79c-4f92-a916-1e4b976041ca",
}


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
        if parent_condition_asset_id != _PARENT_SOURCES[content_rule_key]:
            raise ContentPlanError(
                "the reviewed parent side-altitude condition picture is required"
            )
        source_bytes(parent_condition_asset_id)
        note = content_rule_key == "isosceles-triangle-27327-projection-from-side-sine"
        if note:
            if (
                len(parent_solution_assets) != 1
                or parent_solution_assets[0].get("asset_key") != "image_2"
                or parent_solution_assets[0].get("source_asset_id") != NOTE_SOURCE
                or parent_solution_assets[0].get("url") != "/assets/" + NOTE_SOURCE
            ):
                raise ContentPlanError(
                    "the reviewed parent note figure metadata is required"
                )
        elif parent_solution_assets:
            raise ContentPlanError(
                "the reviewed side-altitude parent has no solution image"
            )
        model = read_context(context).require_rule(content_rule_key)
        content = context["normalized_content"]
        condition = _section(content, "condition")
        changes = prepare_figures(context, condition, generated_solution_assets)
        answer = exact_answer(model.answer)
        plan = diagrams.repair(
            condition,
            _targeted(_section(content, "answer")),
            _targeted(_section(content, "solution")),
            answer,
            render(model, content_rule_key),
            asset_changes=changes,
        )
        return RepairPlan(plan.answer, plan.transformations)
    except (AltitudeSolveError, IsoscelesTrianglePlanError) as exc:
        raise ContentPlanError(str(exc)) from exc
