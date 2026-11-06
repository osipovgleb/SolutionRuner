"""Reviewed parent presentation, renamed labels, optional existing coordinate method."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from midsection_plane_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import condition_text


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_methods_and_native_scene_counts(case):
    result = plan(case)
    html = solution_html(result)
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.find_all("img")) == (2 if case["task"] == "500367" else 1)
    if case["group"] == "485981":
        assert "общим перпендикуляром" in html
        assert result.answer in (r"45^{\circ}", r"60^{\circ}")
    elif case["group"] == "500132":
        if case["task"] == "500588":
            assert "Четырёхугольник A₁BCD₁" in html and "PA₁O" in html and "LCO" in html
        else:
            assert "Четырёхугольник ABC₁D₁" in html and "PAO" in html and "LC₁O" in html
        if case["task"] == "500367":
            assert html.index("Продлим D₁E") < html.index("Метод координат")
        else:
            assert "Метод координат" not in html
    elif case["group"] == "563633":
        assert (
            html.index("Ещё раз применим")
            < html.index("Другой способ")
            < html.index(r"RT=\frac")
        )
    else:
        assert "Пусть T — середина BC" in html
        assert (
            "NK ∥ SA"
            if "точки L и N"
            in condition_text(section(case["context"], "condition")["html"], None)
            else "ML ∥ SA"
        ) in html
        assert "SAB" not in html and "|\\cos\\angle AST|" in html


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_scenes_restore_correct_parent_style_and_condition_labels(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    html = solution_html(result)
    if case["group"] == "641933":
        expected = (
            "0c556cec-ec24-4f11-90a8-1ec7f41ade60"
            if "точки L и N"
            not in condition_text(section(case["context"], "condition")["html"], None)
            else "455e55b1-f138-4c05-9d36-004e3bd4d942"
        )
        assert BeautifulSoup(html, "html.parser").img["data-asset-id"] == expected
        assert "Пусть T — середина BC" in html
    if case["group"] == "563633":
        assert "Другой способ" in html
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unreviewed_source_identity_and_parent_asset_drift_refuse(case):
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_id"]
    a["asset_id"] = uid = "00000000-0000-4000-8000-000000000001"
    a["url"] = "/assets/" + uid
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())


def test_moving_edge_point_across_half_height_selects_compatible_existing_scene():
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == "500132")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert "1: 2" in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace("1: 2", "2: 1") + "</p>"
    result = plan(case, ctx)
    assert (
        BeautifulSoup(solution_html(result), "html.parser").img["data-asset-id"]
        == "7f766a4c-c706-4f4a-a1b6-127427524c37"
    )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


def test_coordinate_figure_in_geometric_slot_is_refused():
    case = next(c for c in CASES if c["task"] == "500367")
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_id"]
    uid = "314372f1-668b-4faf-9750-7617a89fe6b7"
    a["asset_id"] = uid
    a["url"] = "/assets/" + uid
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_known_legacy_scene_is_replaced_when_it_uses_another_parent_presentation():
    import json
    from pathlib import Path

    old = json.loads(
        (Path(__file__).parent / "fixtures/category_15_plane_sources.json").read_text()
    )
    legacy = next(c for c in old["cases"] if c["task"] == "527235")["context"][
        "normalized_content"
    ]["assets"][0]["asset_id"]
    case = next(c for c in CASES if c["task"] == "641933")
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    native = asset["asset_id"]
    assert native != legacy
    asset["asset_id"] = legacy
    asset["url"] = "/assets/" + legacy
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(native, legacy)
    result = plan(case, ctx)
    html = solution_html(result)
    assert BeautifulSoup(html, "html.parser").img["data-asset-id"] == native
    assert "Пусть T — середина BC" in html and "ML ∥ SA" in html
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
