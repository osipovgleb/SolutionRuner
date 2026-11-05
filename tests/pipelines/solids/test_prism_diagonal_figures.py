"""Exact source scenes, role restoration and a single reviewed label correction."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, solution_html
from prism_diagonal_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids import prism_pentagon_cut_svg as svg
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.distance_sources import source_bytes
from solution_runner.pipelines.solids.spatial_distance_model import condition_text


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_figure_order_and_slots_are_preserved(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    soup = BeautifulSoup(solution_html(result), "html.parser")
    keys = [i["data-asset-key"] for i in soup.find_all("img")]
    if case["task"] == "673601":
        assert keys == ["box_distance_solution"]
        assert "G₁" in str(soup) and "CFLN" not in str(soup)
        assert "CK" not in str(soup) and "KD_1" not in str(soup)
    elif case["task"] in {"643676", "643716"}:
        assert keys == ["image_1"]
        assert soup.img["data-asset-id"] == "33d73826-53b8-420c-9560-9ff4f13eac97"
    else:
        assert keys == [a["asset_key"] for a in ctx["normalized_content"]["assets"]]
    if "image_2" in keys:
        html = str(soup)
        assert html.index('data-asset-key="image_1"') < html.index(
            'data-asset-key="image_2"'
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_native_assets_are_refused_before_transformations(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old, uid = asset["asset_id"], "00000000-0000-4000-8000-000000000001"
    asset["asset_id"], asset["url"] = uid, "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_source_correction_replaces_only_the_wrong_glyph_and_preserves_geometry():
    case = next(c for c in CASES if c["task"] == "673601")
    m = selection(case["context"])[0]
    original = ET.fromstring(source_bytes(svg.SOURCE))
    corrected = ET.fromstring(svg.render(m))
    assert original.attrib == corrected.attrib and len(original) == len(corrected)
    for i, (before, after) in enumerate(zip(original, corrected, strict=True)):
        if i != 30:
            assert ET.tostring(before) == ET.tostring(after)
    letter = ET.fromstring(source_bytes(svg.LETTER_SOURCE))[11]
    actual = corrected[30]
    assert actual.attrib == {
        **letter.attrib,
        "id": "label-F",
        "transform": "translate(65.7495 -83.824)",
    }
    assert [e.attrib for e in actual] == [e.attrib for e in letter]
    assert ET.tostring(original[30]) != ET.tostring(actual)
    with pytest.raises(ContentPlanError):
        svg.render(selection(CASES[0]["context"])[0])


def test_all_pentagons_keep_the_parent_projection_method_and_matching_scene():
    for task in ("642779", "643676", "643716"):
        case = next(c for c in CASES if c["task"] == task)
        assert selection(case["context"])[0].symbols["method"] == "projection"
        result = plan(case)
        html = solution_html(result)
        soup = BeautifulSoup(html, "html.parser")
        assert len(soup.find_all("img")) == 1
        assert soup.img["data-asset-id"] == "33d73826-53b8-420c-9560-9ff4f13eac97"
        assert "теореме о трёх перпендикулярах" in html and "подобны" in html
        assert "S_{CKMN}+S_{MLN}" in html and "S_{MKCE}" not in html
        ctx = without_figures(case)
        result = plan(case, ctx)
        replay(ctx, result.transformations)
        assert len(ctx["normalized_content"]["assets"]) == 1
        assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "markup",
    (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="b)">x</li><li data-list-marker="б)">y</li></ol>',
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="a)" data-extra="x">x</li><li data-list-marker="б)">y</li></ol>',
        '<p><i data-extra="x">МKC,</i></p>',
        "<p><i>МKC, дополнительное требование</i></p>",
    ),
)
def test_unreviewed_list_or_italic_variants_still_refuse(markup):
    with pytest.raises(ContentPlanError):
        condition_text(markup, None)
