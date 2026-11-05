"""Three-figure method restoration and strict ownership of the added third slot."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from distance_source_cases import CASES as BOXES
from distance_source_cases import plan as box_plan
from midpoint_source_cases import replay, section, solution_html
from pyramid_midsection_source_cases import CASES as MIDPOINTS
from pyramid_midsection_source_cases import plan as midpoint_plan
from vertical_cut_source_cases import CASES, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import prepare


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if len(c["context"]["normalized_content"]["assets"]) == 3],
    ids=lambda c: c["task"],
)
def test_native_three_scenes_keep_order_captions_and_proof_placement(case):
    result = plan(case)
    soup = BeautifulSoup(solution_html(result), "html.parser")
    row = soup.select_one(
        'li[data-list-marker="а)"] > section[data-layout="media-row"]'
    )
    assert row is not None
    items = row.select('section[data-layout="media-item"]')
    assert len(items) == 3
    assert [p.get_text() for p in row.select("nobr")] == ["Рис. 1", "Рис. 2", "Рис. 3"]
    assert [i.img["data-asset-key"] for i in items] == ["image_1", "image_2", "image_3"]
    assert not soup.select_one('li[data-list-marker="б)"] img')


@pytest.mark.parametrize("task", ("656085", "656255"))
@pytest.mark.parametrize("key", ("image_1", "image_2", "image_3"))
def test_partial_missing_scene_restores_the_same_reviewed_method(task, key):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"] = [
        a for a in ctx["normalized_content"]["assets"] if a["asset_key"] != key
    ]
    sol = section(ctx, "solution")
    soup = BeautifulSoup(sol["html"], "html.parser")
    soup.find("img", attrs={"data-asset-key": key}).decompose()
    sol["html"] = str(soup)
    sol["asset_keys"].remove(key)
    result = plan(case, ctx)
    assert prepare(ctx, ())[0].symbols["method"] == "coincident_feet"
    replay(ctx, result.transformations)
    assert {a["asset_key"] for a in ctx["normalized_content"]["assets"]} == {
        "image_1",
        "image_2",
        "image_3",
    }
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "case,planner",
    [(c, box_plan) for c in BOXES if c["task"] == c["group"]]
    + [(c, midpoint_plan) for c in MIDPOINTS if c["task"] == c["group"]],
    ids=lambda v: v["task"] if isinstance(v, dict) else v.__module__,
)
def test_third_slot_is_refused_in_every_other_reviewed_and_plain_box_mode(
    case, planner
):
    ctx = deepcopy(case["context"])
    asset = deepcopy(ctx["normalized_content"]["assets"][0])
    asset["asset_key"] = "image_3"
    ctx["normalized_content"]["assets"].append(asset)
    sec = section(ctx, "solution")
    sec["html"] += (
        '<p><img data-asset-id="'
        + asset["asset_id"]
        + '" data-asset-key="image_3" data-transformation-target-id="asset:image_3" src="'
        + asset["url"]
        + '"/></p>'
    )
    sec["asset_keys"].append("image_3")
    with pytest.raises(ContentPlanError, match="third spatial diagram"):
        planner(case, ctx)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if len(c["context"]["normalized_content"]["assets"]) == 3],
    ids=lambda c: c["task"],
)
def test_wrong_reviewed_source_in_third_slot_is_refused(case):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    old = assets[2]["asset_id"]
    assets[2]["asset_id"] = assets[1]["asset_id"]
    assets[2]["url"] = assets[1]["url"]
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        old, assets[1]["asset_id"]
    )
    with pytest.raises(ContentPlanError, match="another reviewed slot"):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("656085", "656255"))
def test_parent_scene_cannot_mix_with_the_childrens_two_auxiliary_scenes(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = source = "29df316f-7cb6-4aa0-b1f8-f0e5cc489697"
    asset["url"] = "/assets/" + source
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        old, source
    )
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert prepare(ctx, ())[0].symbols["method"] == "coincident_feet"
    assert len(ctx["normalized_content"]["assets"]) == 3
    assert (
        ctx["normalized_content"]["assets"][0]["asset_id"]
        == "1c6739bb-63b8-419b-a911-d443bc53f196"
    )
    assert not plan(case, ctx).transformations
