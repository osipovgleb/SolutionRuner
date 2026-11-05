"""Check all native methods, published equalities, corrections and stable replay."""

from copy import deepcopy

import pytest
import sympy as sp
from combined_formula_oracle import verify
from combined_source_cases import CASES, GROUPS, arguments, expected, plan, read
from midpoint_source_cases import replay, section
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_method_equalities_actual_answer_and_immutable_context(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    assert sp.simplify(PiParser(result.answer).parse().value - expected(case)) == 0
    verify(result, read(case))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    if section(before, "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(before, "condition")


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_method_pins_and_actual_profile_indices(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    changes = {
        "html": {
            "parent_solution_html": args["parent_solution_html"]
            + "<p>Другой метод.</p>"
        },
        "primary": {"parent_asset_id": "foreign"},
        "assets": {"parent_solution_assets": ({"asset_key": "foreign"},)},
    }
    with pytest.raises(ContentPlanError):
        plan(case, **changes[field])
    p = get_group_profile(group)
    assert p.group_order_index == GROUPS[group]["order_index"]
    assert p.source_group_id == GROUPS[group]["group_uuid"]
    assert p.theme_order_index == 7
    h = get_handler(GROUPS[group]["rule"])
    assert (
        h.strict_frozen_input
        and h.requires_frozen_manifest
        and h.verify_content_readback
    )


@pytest.mark.parametrize("group", GROUPS)
def test_unreviewed_additional_instruction_fails_closed(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ["324341", "324435", "501683"])
def test_child_reverse_question_keeps_parent_method(task):
    case = next(c for c in CASES if c["task"] == task)
    assert (
        read(case).kind
        != read(next(c for c in CASES if c["task"] == case["group"])).kind
    )
    verify(plan(case), read(case))


def test_circumsphere_radius_retained_in_cube_geometry():
    case = next(c for c in CASES if c["task"] == "245355")
    m = read(case)
    assert m.q["r"] == m.given[0]
    assert sp.simplify(m.q["a"] * sp.sqrt(3) - 2 * m.q["r"]) == 0
