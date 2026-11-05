"""Verify original numerical drawings, complete parent methods and stable preparation."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from orthogonal_formula_oracle import verify
from orthogonal_source_cases import CASES, GROUPS, arguments, expected, plan, read
from sphere_formula_oracle import PiParser
from test_orthogonal_geometry import voxel_measures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.orthogonal_sources import DATA


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_exact_volume_and_immutable_context(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
    assert ctx == before
    verify(result, m, DATA["orders"][GROUPS[case["group"]]["rule"]])
    volume, surface = voxel_measures(m.solid.additions, m.solid.cutouts)
    assert m.answer == volume == expected(case) == PiParser(result.answer).parse().value
    assert m.solid.surface == surface
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    for role in ("condition", "source"):
        assert section(ctx, role) == section(before, role)
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_complete_parent_pins_and_real_profile_indices(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    changes = {
        "html": {
            "parent_solution_html": args["parent_solution_html"] + "<p>Иной метод.</p>"
        },
        "primary": {"parent_asset_id": "foreign"},
        "assets": {"parent_solution_assets": ({"asset_key": "foreign"},)},
    }
    with pytest.raises(ContentPlanError):
        plan(case, **changes[field])
    p = get_group_profile(group)
    assert (
        p.source_group_id == GROUPS[group]["group_uuid"]
        and p.group_order_index == GROUPS[group]["order_index"]
        and p.theme_order_index == 4
    )
    h = get_handler(GROUPS[group]["rule"])
    assert (
        h.strict_frozen_input
        and h.requires_frozen_manifest
        and h.verify_content_readback
    )


@pytest.mark.parametrize("group", GROUPS)
def test_unreviewed_instruction_is_not_ignored(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
