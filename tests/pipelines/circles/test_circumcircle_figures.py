"""Verify exact compatible source reuse and complete circumcircle ownership."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, GROUPS, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.circles.circumcircle_figures import (
    SOURCES,
)
from solution_runner.pipelines.circles.quantity_sources import SOURCES as AUDITED
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.right.construction_svg import _tag

ALL_SOURCES = {source for row in SOURCES.values() for source in row}


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
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context) == ()
    replay(context, plan(case).transformations)
    assets = {a["asset_key"]: a for a in context["normalized_content"]["assets"]}
    before = case["context"]["normalized_content"]["assets"]
    assert assets["image_1"]["asset_id"] == (
        before[0]["asset_id"] if before else SOURCES[m.mode][0]
    )
    assert read(context) == m
    assert section(context, "condition")["asset_keys"] == ["image_1"]
    assert section(context, "solution")["asset_keys"] == []
    assert len(assets) == 1


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


@pytest.mark.parametrize("group", GROUPS)
def test_compatible_source_cannot_be_duplicated_by_a_generated_asset(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError, match="no generated copies"):
        plan(case, generated_solution_assets=({"asset_key": "image_1"},))
