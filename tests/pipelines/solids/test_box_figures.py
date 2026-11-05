"""Exact source reuse and fail-closed ownership for unnumbered box figures."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from box_source_cases import CASES, GROUPS, arguments, plan
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.box_sources import SOURCES, source_bytes
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_original_box_sources_keep_exact_bytes_and_have_no_raster_or_text(source):
    raw = source_bytes(source)
    root = ET.fromstring(raw)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert raw == source_bytes(SOURCES[source][0])
    assert not list(root.iter(_tag("text"))) and not list(root.iter(_tag("image")))
    assert len(list(root.iter(_tag("line")))) >= 12


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_figures_keep_source_identity_and_condition_role(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx["normalized_content"]["assets"])
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    replay(ctx, plan(case).transformations)
    assets = ctx["normalized_content"]["assets"]
    expected = (
        before[0]["asset_id"] if before else arguments(case["group"])["parent_asset_id"]
    )
    assert len(assets) == 1 and assets[0]["asset_id"] == expected
    if section(case["context"], "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(case["context"], "condition")
    assert (
        section(ctx, "condition")["asset_keys"] == ["image_1"]
        and section(ctx, "solution")["asset_keys"] == []
    )


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "owner", "unreferenced", "duplicate", "instruction"]
)
def test_unknown_figures_or_changed_question_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    sec = section(ctx, "condition")
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find("img")
    if change == "foreign":
        a["asset_id"], a["url"] = "foreign", "/assets/foreign"
        image["data-asset-id"], image["src"] = a["asset_id"], a["url"]
    elif change == "url":
        a["url"] = image["src"] = "/assets/foreign"
    elif change == "owner":
        other = section(ctx, "solution")
        other["html"] += str(image)
        other["asset_keys"] = ["image_1"]
        image.decompose()
        sec["asset_keys"] = []
    elif change == "unreferenced":
        image.decompose()
        sec["asset_keys"] = []
    elif change == "duplicate":
        ctx["normalized_content"]["assets"].append(deepcopy(a))
    else:
        soup.append(BeautifulSoup("<p>Округлите ответ.</p>", "html.parser"))
    sec["html"] = str(soup)
    if change == "owner" and group in {"27060", "27100", "27101", "27143"}:
        replay(ctx, plan(case, ctx).transformations)
        assert section(ctx, "condition")["asset_keys"] == ["image_1"]
        assert section(ctx, "solution")["asset_keys"] == []
    else:
        with pytest.raises(ContentPlanError):
            plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
def test_compatible_box_figure_cannot_receive_a_generated_duplicate(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=({"asset_key": "image_1"},))
