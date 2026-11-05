"""Verify all native exposed areas, exact source retention and stable preparation."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from orthogonal_surface_cases import CASES, GROUPS, arguments, expected, plan, read
from orthogonal_surface_oracle import verify
from sphere_formula_oracle import PiParser
from test_orthogonal_geometry import voxel_measures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.solids.orthogonal_sources import DATA


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_surface_and_stable_replay_ignore_old_answer(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    m = read(case)
    verify(result, m, DATA["surface_styles"][GROUPS[case["group"]]["rule"]])
    assert (
        m.solid.surface
        == voxel_measures(m.solid.additions, m.solid.cutouts)[1]
        == expected(case)
        == PiParser(result.answer).parse().value
    )
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "condition") == section(before, "condition")
    assert section(ctx, "source") == section(before, "source")
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_method_pins_and_full_theme_indices(group, field):
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
    assert (
        p.source_group_id == GROUPS[group]["group_uuid"]
        and p.group_order_index == GROUPS[group]["order_index"]
        and p.theme_order_index == 3
    )


@pytest.mark.parametrize("group", GROUPS)
def test_additional_instruction_is_not_ignored(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Также найдите объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
