"""Check exact numeric source revisions, roles and use of the child's own givens."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from orthogonal_source_cases import CASES, GROUPS, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_sources import (
    DATA,
    SOURCES,
    source_bytes,
)


def swap_source(context, source):
    for a in context["normalized_content"]["assets"]:
        a["asset_id"], a["url"] = source, "/assets/" + source
    for s in context["normalized_content"]["sections"]:
        soup = BeautifulSoup(s["html"], "html.parser")
        for im in soup.find_all("img"):
            im["data-asset-id"], im["src"] = source, "/assets/" + source
        s["html"] = str(soup)


@pytest.mark.parametrize("source", SOURCES)
def test_exact_numeric_svg_or_png_revision(source):
    raw = source_bytes(source)
    assert (
        hashlib.sha256(raw).hexdigest()
        == SOURCES[source][1]
        == DATA["figures"][source]["sha256"]
    )
    assert (
        raw.startswith(b"\x89PNG")
        if SOURCES[source][0].endswith(".png")
        else b"<svg" in raw
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_numerical_picture_is_never_replaced_or_duplicated(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx["normalized_content"]["assets"])
    result = plan(case, ctx)
    assert all(
        not t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    replay(ctx, result.transformations)
    assert ctx["normalized_content"]["assets"] == before
    assert section(ctx, "condition") == section(case["context"], "condition")
    assert section(ctx, "solution")["asset_keys"] == []
    assert (
        len(
            [
                im
                for s in ctx["normalized_content"]["sections"]
                for im in BeautifulSoup(s["html"], "html.parser").find_all("img")
            ]
        )
        == 1
    )


@pytest.mark.parametrize("group", GROUPS)
def test_unknown_or_other_topology_drawing_is_rejected(group):
    case = next(c for c in CASES if c["task"] == group)
    own = DATA["figures"][
        case["context"]["normalized_content"]["assets"][0]["asset_id"]
    ]["shape"]
    foreign = next(src for src, f in DATA["figures"].items() if f["shape"] != own)
    for src in (foreign, "unknown"):
        ctx = deepcopy(case["context"])
        swap_source(ctx, src)
        with pytest.raises(ContentPlanError):
            plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
def test_missing_numerical_drawing_cannot_be_replaced_by_parent(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"] = []
    c = section(ctx, "condition")
    soup = BeautifulSoup(c["html"], "html.parser")
    soup.img.decompose()
    c["html"], c["asset_keys"] = str(soup), []
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", SOURCES)
def test_transcription_is_bound_to_actual_source_bytes(source, monkeypatch):
    monkeypatch.setitem(DATA["figures"][source], "sha256", "0" * 64)
    with pytest.raises(ContentPlanError):
        source_bytes(source)


def test_current_numeric_diagram_controls_the_result_instead_of_problem_identity():
    case = next(c for c in CASES if c["task"] == "27044")
    child = next(c for c in CASES if c["task"] == "4903")
    ctx = deepcopy(case["context"])
    swap_source(ctx, child["context"]["normalized_content"]["assets"][0]["asset_id"])
    assert plan(case, ctx).answer == "39"


def test_moving_the_numeric_picture_to_solution_does_not_leave_a_defined_question():
    case = CASES[0]
    ctx = deepcopy(case["context"])
    c, s = section(ctx, "condition"), section(ctx, "solution")
    soup = BeautifulSoup(c["html"], "html.parser")
    im = soup.img.extract()
    c["html"], c["asset_keys"] = str(soup), []
    s["html"], s["asset_keys"] = str(im) + s["html"], ["image_1"]
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_generated_diagrams_are_not_used_to_replace_numeric_source_data():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], generated_solution_assets=({"asset_key": "foreign"},))
