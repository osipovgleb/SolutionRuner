"""Marked side equality, projection incidence and reviewed source labels."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from right_pyramid_cut_source_cases import CASES, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import compatible
from solution_runner.pipelines.solids.spatial_distance_model import (
    condition_text,
    read_question,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_other_height_or_cut_labels_restore_the_correct_first_scene(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    correct = old = asset["asset_id"]
    other = next(c for c in CASES if c["task"] != case["task"])["context"][
        "normalized_content"
    ]["assets"][0]["asset_id"]
    asset["asset_id"], asset["url"] = other, "/assets/" + other
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        old, other
    )
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert (
        next(
            a
            for a in ctx["normalized_content"]["assets"]
            if a["asset_key"] == "image_1"
        )["asset_id"]
        == correct
    )
    assert not plan(case, ctx).transformations


def test_parent_equal_side_ticks_cannot_be_reused_on_a_scalene_cut():
    case = CASES[0]
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    section(ctx, "condition")["html"] = "<p>" + raw.replace("MA = 6", "MA = 7") + "</p>"
    m = read_question(section(ctx, "condition")["html"])
    assert m.q["LE2"] != m.q["DE2"]
    assert not compatible(
        m, "a94b39f0-a763-427c-b5f5-48bfafb3d3d6", "solution", "image_1"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("t,be", ((3, 3), (2, 4)))
def test_projection_scene_requires_distinct_interior_foot(t, be):
    case = next(c for c in CASES if c["task"] == "505493")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None).replace(
        "AD = 4 и BE = 2", f"AD = {t} и BE = {be}"
    )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    m = read_question(section(ctx, "condition")["html"])
    assert m.q["foot"] <= 0
    assert not compatible(
        m, "fb9cfe5f-aff1-440f-90c3-fa43f0ff034a", "solution", "image_2"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_midpoint_keeps_cosine_heron_and_projection_with_original_second_scene():
    case = next(c for c in CASES if c["task"] == "505493")
    html = solution_html(plan(case))
    assert (
        html.index("косинус угла FED")
        < html.index("Герона")
        < html.index("Приведём другое решение")
    )
    soup = BeautifulSoup(html, "html.parser")
    assert [i["data-asset-key"] for i in soup.find_all("img")] == ["image_1", "image_2"]
    assert (
        "FE" in soup.get_text() and "FK" in soup.get_text() and "KN" in soup.get_text()
    )


@pytest.mark.parametrize(
    "html,expected",
    (
        ("<p><i>AD = AE = LM</i> = 4.</p>", "AD = AE = LM = 4."),
        ("<p><i>СD</i> = 2.</p>", "CD = 2."),
    ),
)
def test_legacy_geometric_italics_keep_the_complete_equation(html, expected):
    assert condition_text(html, None) == expected


@pytest.mark.parametrize(
    "inner",
    (
        '<i data-unknown="yes">AD=AE=LM</i>',
        "<i><b>AD=AE=LM</b></i>",
        "<i>AD=AE=LM=4</i>",
        "<i>AD=ZX</i>",
    ),
)
def test_changed_italic_markup_or_unreviewed_math_is_refused(inner):
    with pytest.raises(ContentPlanError):
        condition_text("<p>" + inner + "</p>", None)
