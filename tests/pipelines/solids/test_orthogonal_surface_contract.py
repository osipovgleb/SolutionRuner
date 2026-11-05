"""Verify quantity separation, all parent methods and unsupported area identities."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from midpoint_source_cases import section
from orthogonal_surface_cases import CASES, GROUPS, plan, read
from orthogonal_surface_oracle import verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.quadrilaterals.parallelogram.rectangle_proofs import (
    value,
)
from solution_runner.pipelines.solids.orthogonal_shapes import build
from solution_runner.pipelines.solids.orthogonal_sources import DATA
from solution_runner.pipelines.solids.orthogonal_surface_proofs import methods, render


@pytest.mark.parametrize("group", GROUPS)
def test_surface_rule_cannot_silently_answer_a_volume_question(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    original = section(ctx, "condition")["html"].replace("\u00ad", "")
    changed = original.replace("площадь поверхности", "объем")
    assert changed != original
    section(ctx, "condition")["html"] = changed
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
def test_parent_methods_work_at_unseen_lengths_without_answer_constants(group):
    case = next(c for c in CASES if c["task"] == group)
    source = case["context"]["normalized_content"]["assets"][0]["asset_id"]
    record = DATA["figures"][source]
    given = [str(2 * int(v)) for v in record["given"]]
    m = build(record["shape"], given)
    style = DATA["surface_styles"][GROUPS[group]["rule"]]
    html = render(m, style)
    result = SimpleNamespace(
        answer=value(m.solid.surface),
        transformations=(
            {
                "transformation_target_id": "section:solution:1",
                "operation": "rewrite",
                "value": {"html": html},
            },
        ),
    )
    verify(result, m, style)
    assert m.solid.surface == 4 * read(case).solid.surface


@pytest.mark.parametrize("group", ["25601", "25621", "25701", "25721"])
def test_both_supplied_parent_methods_remain_complete_and_ordered(group):
    case = next(c for c in CASES if c["task"] == group)
    style = DATA["surface_styles"][GROUPS[group]["rule"]]
    assert len(methods(read(case), style)) == 2
    html = next(
        t["value"]["html"]
        for t in plan(case).transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert html.index("Первый способ") < html.index("Второй способ")
    assert "смиритесь" not in html and "не верит" not in html


@pytest.mark.parametrize(
    "kind,given,style",
    [
        ("bar", (4, 3, 1, 2, 1), {"method": "reduced_xz", "orders": []}),
        ("through_plate", (7, 1, 5, 2, 1), {"method": "corner_grouped", "orders": []}),
        (
            "through_plate",
            (7, 1, 5, 2, 1),
            {"method": "glued_two", "orders": [(0, 1, 2), (0, 1, 2)]},
        ),
    ],
)
def test_a_numerical_identity_must_be_proved_for_the_actual_topology(
    kind, given, style
):
    with pytest.raises(ContentPlanError):
        render(build(kind, given), style)


def test_unmarked_shelf_gaps_are_not_claimed_to_be_equal():
    case = next(c for c in CASES if c["task"] == "25705")
    html = next(
        t["value"]["html"]
        for t in plan(case).transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert "Их сумма G" in html and "равные промежутки" not in html
