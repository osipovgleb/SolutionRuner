"""Check actual triangle strokes, source reuse, angle marks and strict metadata."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from test_box_vertex_angles import condition, verify_proof
from test_distance_figures import vertices_from_svg
from vertex_angle_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.box_vertex_angle_model import segments
from solution_runner.pipelines.solids.vertex_angle_sources import SOURCES, source_bytes
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_all_reviewed_source_bytes_are_pinned(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    assert raw == source_bytes(SOURCES[source][0])
    assert not list(ET.fromstring(raw).iter(_tag("image")))


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "requested,given",
    [
        ("ABD_1", "AB=5, AD=4, AA_1=3"),
        ("AC_1B_1", "AB=15, AD=17, AA_1=8"),
        ("B_1DD_1", "AB=12, AD=9, AA_1=15"),
        ("C_1BC", "AB=5, AD=4, AA_1=4"),
        ("B_1A_1B", "AB=2, AD=3, AA_1=2"),
        ("ABD_1", r"AB=\sqrt{5}, AD=1, AA_1=2"),
    ],
)
def test_real_triangle_helpers_affine_vertices_numbers_and_marker(
    group, requested, given
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    # Preserve the reviewed condition figure while changing only the complete question.
    from bs4 import BeautifulSoup

    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    section(ctx, "condition")["html"] = condition(requested, given).replace(
        "<p>", "<p>" + str(image), 1
    )
    handler = get_handler(GROUPS[group]["rule"])
    specs = handler.diagram_specs(ctx)
    m = read({**case, "context": ctx})
    assert len(specs) <= 1
    for spec in specs:
        root = ET.fromstring(spec["svg_text"])
        vertices = vertices_from_svg(root)
        helpers = {}
        for node in root.findall(_tag("line")):
            name = node.get("id", "")
            if not name.startswith("helper-"):
                continue
            a, b = name.removeprefix("helper-").split("-")
            helpers[a, b] = node
            for vertex, suffix in [(a, "1"), (b, "2")]:
                assert (
                    tuple(float(node.get(axis + suffix)) for axis in ("x", "y"))
                    == vertices[vertex]
                )
        assert set(helpers) == set(segments(m))
        assert (root.find(".//*[@id='requested-angle']") is not None) == (
            group == "245363"
        )
        assert (
            len(
                [
                    n
                    for n in root.findall(_tag("text"))
                    if n.get("id", "").startswith("length-")
                ]
            )
            == 3
        )
        assert (
            len(
                [
                    g
                    for g in root.findall(_tag("g"))
                    if g.get("id", "").startswith("vertex-")
                ]
            )
            == 8
        )
    result = plan(case, ctx)
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "case,field",
    [
        (case, field)
        for case in CASES
        for field in ("foreign", "url", "owner", "duplicate", "instructions")
        if case["context"]["normalized_content"]["assets"] or field == "instructions"
    ],
    ids=lambda item: item["task"] if isinstance(item, dict) else item,
)
def test_metadata_and_unknown_instructions_fail_closed(case, field):
    ctx = deepcopy(case["context"])
    if field == "instructions":
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    else:
        asset = ctx["normalized_content"]["assets"][0]
        if field == "foreign":
            asset["asset_id"] = "foreign"
        elif field == "url":
            asset["url"] = "https://example.com/figure.svg"
        elif field == "owner":
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
            image = soup.find("img")
            image["data-asset-key"] = "image_2"
            image["data-transformation-target-id"] = "asset:image_2"
            section(ctx, "condition")["html"] = str(soup)
            section(ctx, "condition")["asset_keys"] = ["image_2"]
            asset["asset_key"] = "image_2"
        else:
            ctx["normalized_content"]["assets"].append(deepcopy(asset))
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
