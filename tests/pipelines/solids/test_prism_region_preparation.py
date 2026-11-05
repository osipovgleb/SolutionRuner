"""Check native vertex subsets, source errors, parent methods and exact replay."""

from copy import deepcopy

import pytest
import sympy as sp
from midpoint_source_cases import replay, section, solution_html
from prism_region_oracle import verify
from prism_region_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_model import read_question


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_proof_each_equality_and_immutable_input(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    assert (
        PiParser(result.answer).parse().value
        == PiParser(saved_answer(case)).parse().value
    )
    verify(result, read(case))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    if section(before, "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(before, "condition")


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_pins_and_profiles(group, field):
    c = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    overrides = {
        "html": {
            "parent_solution_html": args["parent_solution_html"]
            + "<p>Другой метод.</p>"
        },
        "primary": {"parent_asset_id": "foreign"},
        "assets": {"parent_solution_assets": ({"asset_key": "foreign"},)},
    }
    with pytest.raises(ContentPlanError):
        plan(c, **overrides[field])
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    assert (
        profile.group_order_index == GROUPS[group]["order_index"]
        and profile.source_group_id == GROUPS[group]["group_uuid"]
    )
    assert (
        handler.strict_frozen_input
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )


@pytest.mark.parametrize(
    "vertices,body",
    [
        ("A,B,B_1,A_1", "треугольной"),
        ("A,B,C,A_1,A_1", "треугольной"),
        ("A,B,C", "треугольной"),
        ("A,B,C,D_1", "треугольной"),
        ("A,C,E,A_1,C_1,E_1", "шестиугольной"),
        ("A,B,C,A_1,B_1", "шестиугольной"),
    ],
)
def test_unreviewed_or_degenerate_vertex_subsets_fail_closed(vertices, body):
    names = "ABCA_1B_1C_1" if body == "треугольной" else "ABCDEFA_1B_1C_1D_1E_1F_1"
    with pytest.raises(ContentPlanError):
        read_question(
            "<p>Найдите объем многогранника, вершинами которого являются точки "
            + vertices
            + " правильной "
            + body
            + " призмы "
            + names
            + ", площадь основания которой равна 3, а боковое ребро равно 5.</p>"
        )


@pytest.mark.parametrize(
    "tail", [" Округлите до сотых.", " При условии, что призма наклонная."]
)
def test_extra_instruction_fails_closed(tail):
    c = CASES[0]
    ctx = deepcopy(c["context"])
    section(ctx, "condition")["html"] += "<p>" + tail + "</p>"
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_actual_removed_pyramid_names_and_quadrilateral_note_are_preserved():
    c = next(c for c in CASES if c["task"] == "266747")
    html = solution_html(plan(c))
    assert "ABCC₁" in html and "A₁B₁C₁B" not in html
    c = next(c for c in CASES if c["task"] == "268183")
    html = solution_html(plan(c))
    assert "<b>Примечание.</b>" in html and "ABC" in html and "DEF" in html


def test_exact_fractional_dimensions_are_computed_without_saved_answers():
    m = read_question(
        r"<p>Найдите объем многогранника, вершинами которого являются точки A,B,C,A_1 правильной треугольной призмы ABCA_1B_1C_1, площадь основания которой равна 1.5, а боковое ребро равно 2\sqrt{3}.</p>"
    )
    assert m.answer == sp.sqrt(3)
