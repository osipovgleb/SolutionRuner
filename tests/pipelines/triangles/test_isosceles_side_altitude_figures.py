"""Validate all role permutations, source reuse and generated figure replay."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_altitude_cases import CASES, plan, section
from test_isosceles_side_altitude_model import projection_geometry
from test_isosceles_side_altitude_proofs import verify_rows
from test_two_ray_source_methods import replay

from solution_runner.pipelines.triangles.isosceles.side_altitude_figures import (
    selection,
)
from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    read_context,
)
from solution_runner.pipelines.triangles.isosceles.side_altitude_sources import (
    SOURCES,
    source_bytes,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def synthetic(frame, kind, topology):
    case = next(
        c for c in CASES if c["task"] == ("27328" if kind == "side" else "27322")
    )
    ctx = deepcopy(case["context"])
    p, q, r = frame
    equal = "".join(sorted((p, r))) + "=" + "".join(sorted((q, r)))
    given = (
        equal + "=10"
        if kind == "side"
        else equal
        + ", "
        + "".join(sorted((p, q)))
        + (r"=10\sqrt{2}" if topology == 0 else "=10")
    )
    value = {-1: r"\frac{3}{5}", 0: r"\frac{\sqrt{2}}{2}", 1: r"\frac{4}{5}"}[topology]
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        "<p>"
        + str(image)
        + "В треугольнике ABC "
        + given
        + r", \cos "
        + q
        + p
        + r
        + "="
        + value
        + ". Найдите высоту "
        + p
        + "H.</p>"
    )
    return case, ctx


@pytest.mark.parametrize(
    "frame", list(itertools.permutations("ABC")), ids=lambda f: "".join(f)
)
@pytest.mark.parametrize("kind", ["base", "side"])
@pytest.mark.parametrize("topology", [-1, 0, 1])
def test_all_vertex_permutations_and_topologies_prepare_and_replay_without_drift(
    frame, kind, topology
):
    case, ctx = synthetic(frame, kind, topology)
    m = read_context(ctx)
    result = plan(case, ctx)
    assert m.topology == topology and (m.vertex, m.other_base_vertex, m.apex) == frame
    value = {-1: sp.Rational(3, 5), 0: sp.sqrt(2) / 2, 1: sp.Rational(4, 5)}[topology]
    length = 10 if kind == "side" or topology else 10 * sp.sqrt(2)
    oracle = projection_geometry(kind, length, "cos", value)
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    verify_rows(html, m, oracle)
    _, _, mode, _, source, diagram = selection(ctx)
    expected = (m.vertex, m.other_base_vertex, m.apex, kind == "side", topology)
    if mode in {"native", "crop"}:
        assert SOURCES[source][1:6] == expected
    if diagram:
        root = ET.fromstring(diagram["svg_text"])
        left, top, w, h = map(float, root.get("viewBox").split())
        for g in root.findall("s:g", NS):
            transform = g.get("transform", "")
            dx = dy = 0
            if transform:
                dx, dy = map(
                    float,
                    re.fullmatch(r"translate\(([^ ]+) ([^)]+)\)", transform).groups(),
                )
            for rect in g.findall(".//s:rect", NS):
                x, y = float(rect.get("x", 0)) + dx, float(rect.get("y", 0)) + dy
                assert left - 1e-5 <= x and top - 1e-5 <= y
                assert (
                    x + float(rect.get("width")) <= left + w + 1e-5
                    and y + float(rect.get("height")) <= top + h + 1e-5
                )
        ids = [n.get("id") for n in root.iter() if n.get("id")]
        assert len(ids) == len(set(ids))
        if mode == "crop":
            old = ET.fromstring(source_bytes(source))
            assert [ET.tostring(n) for n in root] == [ET.tostring(n) for n in old]
    replay(ctx, result.transformations)
    assert (
        len(ctx["normalized_content"]["assets"]) == 1
        and plan(case, ctx).transformations == ()
    )


@pytest.mark.parametrize("source", list(SOURCES))
def test_all_original_source_bytes_are_present_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


def test_already_attached_correct_note_drawing_is_reused_in_condition():
    case = next(c for c in CASES if c["task"] == "27327")
    *_, mode, key, source, diagram = selection(case["context"])
    assert (
        mode == "native"
        and key == "image_1"
        and source == "cb42a1f2-647b-46d4-8694-ef6fa14a4cdf"
        and diagram is None
    )
