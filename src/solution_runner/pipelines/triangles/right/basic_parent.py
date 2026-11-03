"""Prepare elementary parent methods using the shared exact right-triangle solver."""

from bs4 import BeautifulSoup

from ...probability import solution_diagrams as diagrams
from .altitude_input import canonical_condition
from .altitude_parent import _display, _source, exact_answer
from .altitude_solver import AltitudeSolveError, solve_altitude_condition
from .basic_methods import read_parent, validate_child
from .basic_proofs import render

_SOURCES = {
    "8f8988bb-fa85-47a8-be0e-75edaf5a7604": "894f231be7e3206f4d27781c309abc420d27ef8a8a683aaed9683de09e5803b8",
    "e95a7071-cff1-477d-85ca-a4b51bbb68b3": "db43f0f53fa7ee996ef0f8605ca3265ea912f50264fdf3d76267cb141427d4c2",
}


def _figure(content, condition, source, *, sources=None):
    from .planner import _asset_transformation

    _source(source, sources=_SOURCES if sources is None else sources)
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    assets = content.get("assets", [])
    if not isinstance(assets, list):
        raise AltitudeSolveError("normalized triangle assets must be a list")
    if not assets and not images:
        return (_asset_transformation(source),)
    if (
        len(assets) != 1
        or not isinstance(assets[0], dict)
        or len(images) > 1
        or assets[0].get("asset_key") != "image_1"
        or assets[0].get("asset_id") != source
        or assets[0].get("kind") != "ordinary_image"
        or assets[0].get("url") != "/assets/" + source
        or condition.get("asset_keys", ["image_1"]) != ["image_1"]
    ):
        raise AltitudeSolveError(
            "the basic triangle must retain its audited condition figure"
        )
    return ()


def _targeted(section):
    if (
        section is None
        or section.get("transformation_target_id")
        or not section.get("section_id")
    ):
        return section
    identifier = str(section["section_id"])
    target = (
        identifier if identifier.startswith("section:") else "section:" + identifier
    )
    return {**section, "transformation_target_id": target}


def prepare(
    context,
    *,
    parent_asset_id,
    parent_solution_html,
    required_trig_name=None,
    required_requested=None,
):
    from .planner import RepairPlan, _section

    kind = read_parent(parent_solution_html)
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise AltitudeSolveError("schema-v3 normalized content is required")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise AltitudeSolveError("a complete condition is required")
    solved = solve_altitude_condition(
        canonical_condition(condition["html"], source=parent_asset_id)
    )
    validate_child(kind, solved)
    if required_trig_name is not None and required_trig_name + "A" not in {
        k for k, _, _ in solved.givens
    }:
        raise AltitudeSolveError(
            "the child must use the registered trigonometric function"
        )
    if required_requested is not None and solved.requested != required_requested:
        raise AltitudeSolveError("the child must request the registered side")
    figure_changes = _figure(content, condition, parent_asset_id)
    answer = exact_answer(solved.exact_value)
    html = render(kind, solved, _display(solved), answer)
    plan = diagrams.repair(
        condition,
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        answer,
        html,
        asset_changes=figure_changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
