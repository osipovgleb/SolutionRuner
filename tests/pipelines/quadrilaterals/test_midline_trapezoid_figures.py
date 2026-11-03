"""Verify exact unnumbered schematic reuse, geometric properties and refusals."""

import hashlib
import math
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midline_trapezoid_source_cases import CASES, GROUPS, plan, read
from midpoint_source_cases import replay, section

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.quadrilaterals.trapezoid.midline_figures import (
    DETAIL,
    SOURCES,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.quantity_sources import (
    SOURCES as AUDITED,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.quantity_sources import (
    source_bytes,
)
from solution_runner.pipelines.triangles.right.construction_svg import _tag


def points(line):
    return tuple(tuple(float(line.get(axis + str(i))) for axis in "xy") for i in (1, 2))


def vector(line):
    a, b = points(line)
    return b[0] - a[0], b[1] - a[1]


@pytest.mark.parametrize(
    "source", sorted({s for row in SOURCES.values() for s in row} | {DETAIL})
)
def test_audited_source_bytes_labels_and_unnumbered_schematic(source):
    data = source_bytes(source)
    assert hashlib.sha256(data).hexdigest() == AUDITED[source][1]
    root = ET.fromstring(data)
    assert not list(root.iter(_tag("text")))
    assert not list(root.iter(_tag("image")))
    glyphs = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    assert len(glyphs) == (
        8
        if source == DETAIL
        else 7
        if source in {SOURCES["diagonal_piece"][0], SOURCES["perpendicular"][0]}
        else 6
        if source
        in {
            *SOURCES["large_base"],
            *SOURCES["perimeter_midline"],
            *SOURCES["diagonal_midpoints"],
        }
        else 5
        if source in {*SOURCES["cut_perimeter"], *SOURCES["base_parts"]}
        else 4
    )
    lines = root.findall(_tag("line"))
    sides = [e for e in lines if e.get("stroke") == "#0D0F0F"][-4:]
    horizontal = [e for e in sides if abs(vector(e)[1]) < 0.1]
    assert len(horizontal) == 2
    base_lengths = sorted(math.dist(*points(e)) for e in horizontal)
    assert base_lengths[1] > base_lengths[0] > 0
    if source in {
        *SOURCES["large_base"],
        *SOURCES["perimeter_midline"],
        SOURCES["diagonal_piece"][0],
        SOURCES["base_parts"][0],
    }:
        color = "#007EA5" if source == SOURCES["base_parts"][0] else "#143B8F"
        median = next(e for e in lines if e.get("stroke") == color)
        assert abs(vector(median)[1]) < 0.001
        assert math.dist(*points(median)) == pytest.approx(
            sum(base_lengths) / 2, rel=0.003
        )
    if source == SOURCES["cut_perimeter"][0] or source == SOURCES["cut_perimeter"][1]:
        parallel = next(e for e in lines if e.get("stroke") == "#143B8F")
        right = max(
            (e for e in sides if abs(vector(e)[1]) > 1),
            key=lambda e: sum(p[0] for p in points(e)),
        )
        u, v = vector(parallel), vector(right)
        assert abs(u[0] * v[1] - u[1] * v[0]) / math.hypot(*u) / math.hypot(*v) < 0.001
    if source == SOURCES["perpendicular"][0]:
        diagonals = [e for e in lines if e.get("stroke") == "#143B8F"]
        u, v = map(vector, diagonals)
        assert abs(u[0] * v[0] + u[1] * v[1]) / math.hypot(*u) / math.hypot(*v) < 0.001
        height = next(e for e in lines if e.get("stroke") == "#007EA5")
        assert math.dist(*points(height)) == pytest.approx(
            sum(base_lengths) / 2, rel=0.001
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_case_keeps_exact_asset_identifiers_urls_and_properties(case):
    model = read(case["context"])
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(case["context"]) == ()
    context = deepcopy(case["context"])
    replay(context, plan(case).transformations)
    assert (
        context["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    asset = context["normalized_content"]["assets"][0]
    assert asset["asset_id"] in SOURCES[model.mode]
    if model.mode == "diagonal_midpoints":
        methods = BeautifulSoup(
            section(context, "solution")["html"], "html.parser"
        ).select("section")
        assert methods[0].find("img")["data-asset-id"] == DETAIL
        assert not methods[1].find("img")


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change",
    ["foreign", "url", "extra_instruction", "duplicate", "unreferenced", "wrong_owner"],
)
def test_unknown_or_misowned_figures_and_instructions_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    condition = section(context, "condition")
    asset = context["normalized_content"]["assets"][0]
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
    elif change == "wrong_owner":
        image.extract()
        solution = section(context, "solution")
        solution["html"] = str(image) + solution["html"]
        solution["asset_keys"].insert(0, "image_1")
        condition["asset_keys"] = []
    else:
        soup.append(BeautifulSoup("<p>Округлите ответ до целого.</p>", "html.parser"))
    condition["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)
