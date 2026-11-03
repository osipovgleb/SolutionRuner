"""Verify exact compatible source reuse and complete chord/tangent ownership."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from tangent_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.circles.quantity_sources import SOURCES as AUDITED
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.circles.tangent_figures import (
    DETAILS,
    LEGACY_TANGENT,
    SOURCES,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.right.construction_svg import _tag

ALL_SOURCES = (
    {source for row in SOURCES.values() for source in row}
    | set(DETAILS.values())
    | {LEGACY_TANGENT}
)


@pytest.mark.parametrize("source", sorted(ALL_SOURCES))
def test_original_unnumbered_figures_have_exact_reviewed_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == AUDITED[source][1]
    root = ET.fromstring(raw)
    assert not list(root.iter(_tag("text"))) and not list(root.iter(_tag("image")))
    assert len(root.findall(_tag("line"))) >= 2
    assert list(root.iter(_tag("path")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_case_reuses_matching_figure_roles_and_original_ids(case):
    context = deepcopy(case["context"])
    m = read(context)
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context) == ()
    replay(context, plan(case).transformations)
    assets = {a["asset_key"]: a for a in context["normalized_content"]["assets"]}
    before = case["context"]["normalized_content"]["assets"][0]
    assert assets["image_1"]["asset_id"] == before["asset_id"]
    assert assets["image_1"]["url"] == before["url"]
    assert section(context, "condition") == section(case["context"], "condition")
    assert section(context, "condition")["asset_keys"] == ["image_1"]
    if m.mode in DETAILS:
        assert assets["image_2"]["asset_id"] == DETAILS[m.mode]
        assert section(context, "solution")["asset_keys"] == ["image_2"]
        assert len(assets) == 2
    else:
        assert len(assets) == 1 and section(context, "solution")["asset_keys"] == []
    if m.mode == "central_from_tangent":
        assert assets["image_2"]["asset_id"] != LEGACY_TANGENT
        assert DETAILS[m.mode] == "ce2fa07b-34f1-44dc-833f-deb1f5d7af2d"


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "instruction", "duplicate", "unreferenced", "owner"]
)
def test_foreign_or_misowned_assets_and_unknown_instructions_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    asset = context["normalized_content"]["assets"][0]
    condition = section(context, "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    if change == "foreign":
        asset["asset_id"], asset["url"] = "foreign", "/assets/foreign"
        image["data-asset-id"], image["src"] = "foreign", "/assets/foreign"
    elif change == "url":
        asset["url"] = "/assets/other"
    elif change == "duplicate":
        soup.append(deepcopy(image))
    elif change == "unreferenced":
        image.decompose()
        condition["asset_keys"] = []
    elif change == "owner":
        image.extract()
        condition["asset_keys"] = []
        solution = section(context, "solution")
        solution["html"] = str(image) + solution["html"]
        solution["asset_keys"].insert(0, "image_1")
    else:
        soup.append(BeautifulSoup("<p>Округлите ответ.</p>", "html.parser"))
    condition["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("group", ["27858", "27862", "27878"])
def test_solution_picture_cannot_be_replaced_with_a_condition_picture(group):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    asset = context["normalized_content"]["assets"][1]
    old = asset["asset_id"]
    new = context["normalized_content"]["assets"][0]["asset_id"]
    asset["asset_id"], asset["url"] = new, "/assets/" + new
    solution = section(context, "solution")
    solution["html"] = solution["html"].replace(old, new)
    with pytest.raises(ContentPlanError):
        plan(case, context)
