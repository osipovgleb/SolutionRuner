"""Verify exact cylinder source identities, roles and compatible unnumbered diagrams."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from cylinder_source_cases import CASES, GROUPS, plan
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.cylinder_sources import (
    PARENTS,
    SOURCES,
    source_bytes,
)

PICTURED = tuple(c for c in CASES if c["context"]["normalized_content"]["assets"])


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_source_bytes_are_exact_without_embedded_raster(source):
    raw = source_bytes(source)
    assert (
        hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
        and b"<svg" in raw
        and b"<image" not in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_reuse_and_parent_picture_roles_without_new_copies(case):
    ctx = deepcopy(case["context"])
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(ctx) == ()
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    primary, solution_assets, _ = PARENTS[handler.key]
    if primary is None:
        assert ctx["normalized_content"]["assets"] == []
    else:
        assert len(ctx["normalized_content"]["assets"]) == 1
        role = "solution" if solution_assets else "condition"
        assert section(ctx, role)["asset_keys"] == ["image_1"]
        if role == "solution":
            assert section(ctx, "condition")["asset_keys"] == []
            soup = BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
            assert (
                soup.find("p").get_text(strip=True) == ""
                and soup.find("p").find("img") is not None
            )
    if case["task"] in {"284362", "285799", "285839", "285801"}:
        assert (
            ctx["normalized_content"]["assets"][0]["asset_id"]
            == "f421f999-42e5-497b-8387-9b0a26dcf645"
        )


@pytest.mark.parametrize("case", PICTURED, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "unreferenced", "wrong_object"]
)
def test_unreviewed_or_incompatible_assets_fail_closed(case, field):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if field == "foreign":
        a["asset_id"] = "foreign"
    elif field == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif field == "duplicate":
        assets.append(deepcopy(a))
    elif field == "unreferenced":
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                img.decompose()
            s["html"] = str(soup)
            s["asset_keys"] = []
    else:
        other = (
            "3b0fb301-3f6f-4c93-ae42-89c547017e1e"
            if case["group"] != "27173"
            else "d9a6d82b-867c-4e92-9008-ad8effb419c2"
        )
        a["asset_id"] = other
        a["url"] = "/assets/" + other
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                img["data-asset-id"] = other
                img["src"] = "/assets/" + other
            s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", ["27045", "284362"])
def test_condition_and_solution_picture_cannot_exchange_roles(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    source = "solution" if group == "284362" else "condition"
    target = "condition" if source == "solution" else "solution"
    s = section(ctx, source)
    soup = BeautifulSoup(s["html"], "html.parser")
    img = str(soup.img)
    soup.img.decompose()
    s["html"] = str(soup)
    s["asset_keys"] = []
    t = section(ctx, target)
    t["html"] = "<p>" + img + "</p>" + t["html"]
    t["asset_keys"] = ["image_1"]
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
