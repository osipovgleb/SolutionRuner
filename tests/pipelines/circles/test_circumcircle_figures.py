"""Verify exact compatible source reuse and complete circumcircle ownership."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, GROUPS, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.circles.circumcircle_figures import (
    DETAILS,
    SOURCES,
)
from solution_runner.pipelines.circles.circumcircle_polygon_figures import KEY
from solution_runner.pipelines.circles.circumcircle_polygon_svg import SOURCE
from solution_runner.pipelines.circles.quantity_sources import SOURCES as AUDITED
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.right.construction_svg import _tag

ALL_SOURCES = {source for row in SOURCES.values() for source in row} | {
    source for row in DETAILS.values() for _, source in row
}


@pytest.mark.parametrize("source", sorted(ALL_SOURCES))
def test_original_unnumbered_figures_have_exact_reviewed_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == AUDITED[source][1]
    root = ET.fromstring(raw)
    assert not list(root.iter(_tag("text"))) and not list(root.iter(_tag("image")))
    assert list(root.iter(_tag("line"))) or list(root.iter(_tag("polygon")))
    assert list(root.iter(_tag("path")))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_case_reuses_matching_figure_roles_and_original_ids(case):
    context = deepcopy(case["context"])
    m = read(context)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context)
    assert len(specs) == (1 if m.mode == "polygon_vertices" and m.answer != 5 else 0)
    replay(context, plan(case).transformations)
    assets = {a["asset_key"]: a for a in context["normalized_content"]["assets"]}
    if m.mode == "polygon_vertices":
        key = KEY if specs else "image_1"
        assert len(assets) == 1
        assert assets[key]["asset_id"] == (
            "preview-" + specs[0]["sha256"][:16] if specs else SOURCE
        )
        assert section(context, "condition") == section(case["context"], "condition")
        assert section(context, "solution")["asset_keys"] == [key]
        soup = BeautifulSoup(section(context, "solution")["html"], "html.parser")
        first, second = soup.select("section")
        assert first.find_all("p")[-1].find("img") and not second.find("img")
        assert read(context) == m
        return
    before = case["context"]["normalized_content"]["assets"]
    assert assets["image_1"]["asset_id"] == (
        "0676249d-0639-4ff4-9c2b-bdfacc3f5390"
        if case["task"] == "516291"
        else before[0]["asset_id"]
        if before
        else SOURCES[m.mode][0]
    )
    assert read(context) == m
    assert section(context, "condition")["asset_keys"] == ["image_1"]
    details = DETAILS.get(m.mode, ())
    keys = ["image_" + str(i + 2) for i in range(len(details))]
    for key, (_, source) in zip(keys, details):
        assert assets[key]["asset_id"] == source
    assert section(context, "solution")["asset_keys"] == keys
    assert len(assets) == 1 + len(details)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "instruction", "duplicate", "unreferenced", "owner"]
)
def test_foreign_or_misowned_assets_and_unknown_instructions_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    asset = context["normalized_content"]["assets"][0]
    owner = "solution" if group == "27930" else "condition"
    condition = section(context, owner)
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
        solution = section(context, "condition" if owner == "solution" else "solution")
        solution["html"] = str(image) + solution["html"]
        solution["asset_keys"].insert(0, "image_1")
    else:
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
        if owner == "condition":
            soup.append(BeautifulSoup("<p>Округлите ответ.</p>", "html.parser"))
    condition["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("group", GROUPS)
def test_compatible_source_cannot_be_duplicated_by_a_generated_asset(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError, match="no generated copies"):
        plan(case, generated_solution_assets=({"asset_key": "image_1"},))
