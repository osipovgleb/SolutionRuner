"""Check original SVG geometry, all actual vertex frames and unclipped lettering."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from isosceles_obtuse_cases import CASES, plan, section
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.isosceles.obtuse_figures import (
    SOURCE,
    selection,
    source_bytes,
)
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
def test_label_permutations_preserve_geometry_and_empty_replay(frame):
    p, q, r = frame
    case = CASES[0]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В тупоугольном треугольнике ABC {p + r}={q + r}=10, высота {p}H равна 5. Найдите синус угла {p + r + q}.</p>"
    )
    model, _, _, diagram = selection(ctx)
    assert (model.vertex, model.other_base_vertex, model.apex) == frame
    original, rendered = (
        ET.fromstring(source_bytes()),
        ET.fromstring(diagram["svg_text"]),
    )
    glyphs = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    generated = [g for g in rendered.findall(_tag("g")) if list(g.iter(_tag("path")))]
    canonical = dict(zip("ABCH", glyphs))
    assert len(generated) == 4
    for expected, actual in zip((p, q, r, "H"), generated):
        assert [e.attrib for e in actual.iter(_tag("path"))] == [
            e.attrib for e in canonical[expected].iter(_tag("path"))
        ]
    # Only outlined labels and the root canvas may change.
    geometry = lambda root: [
        ET.tostring(e)
        for e in root
        if e not in root.findall(_tag("g")) or not list(e.iter(_tag("path")))
    ]
    assert geometry(original) == geometry(rendered)
    left, top, width, height = map(float, rendered.get("viewBox").split())
    for g in generated:
        dx = dy = 0
        if g.get("transform"):
            dx, dy = map(
                float,
                re.fullmatch(
                    r"translate\(([^ ]+) ([^)]+)\)", g.get("transform")
                ).groups(),
            )
        x, y, w, h = _bounds(g)
        assert left <= x + dx and top <= y + dy
        assert x + dx + w <= left + width and y + dy + h <= top + height
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("kind", ["reference", "url", "key", "source"])
def test_unknown_or_mismatched_primary_identity_is_rejected(kind):
    ctx = deepcopy(CASES[0]["context"])
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            SOURCE, "other"
        )
    elif kind == "url":
        asset["url"] = "/assets/other"
    elif kind == "key":
        asset["asset_key"] = "editorial_figure"
    else:
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    with pytest.raises(ContentPlanError):
        selection(ctx)
