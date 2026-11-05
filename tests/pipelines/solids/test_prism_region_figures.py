"""Check highlighted native vertex sets, exact restoration and unknown source rejection."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from prism_region_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_sources import DATA, source_bytes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_sources_roles_and_missing_exact_scene_restoration(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    m = read(case)
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    for a in before["normalized_content"]["assets"]:
        assert a in ctx["normalized_content"]["assets"]
    assets = {a["asset_key"]: a for a in ctx["normalized_content"]["assets"]}
    assert set(assets) == {"image_1", "image_2"}
    assert section(ctx, "condition")["asset_keys"] == ["image_1"]
    assert section(ctx, "solution")["asset_keys"] == ["image_2"]
    assert (
        len(
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 1
    )
    src = assets["image_2"]["asset_id"]
    assert source_bytes(src)
    assert any(
        s["source"] == src
        and s["body"] == m.body
        and s["vertices"] == sorted(m.vertices)
        for s in DATA["region_scenes"]
    )
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("task", ["245340", "245341", "245342", "245343", "245344"])
@pytest.mark.parametrize("change", ["foreign", "url", "role", "duplicate"])
def test_native_figure_identity_and_roles_are_strict(task, change):
    c = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(c["context"])
    a = ctx["normalized_content"]["assets"][0]
    if change == "foreign":
        a["asset_id"] = "foreign"
    elif change == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif change == "duplicate":
        ctx["normalized_content"]["assets"].append(deepcopy(a))
    else:
        section(ctx, "solution")["asset_keys"].append(a["asset_key"])
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_changed_vertices_cannot_reuse_old_highlighted_solution():
    c = CASES[0]
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    s["html"] = s["html"].replace(
        'data-math-identifier="A">A</var><sub>1</sub> пра',
        'data-math-identifier="B">B</var><sub>1</sub> пра',
    )
    assert s["html"] != section(c["context"], "condition")["html"]
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_redundant_generated_copy_is_rejected():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], generated_solution_assets=({"asset_key": "foreign"},))
