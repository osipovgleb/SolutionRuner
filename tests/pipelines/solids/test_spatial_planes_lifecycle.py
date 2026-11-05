"""Local fake transport exercises source guards and ratio diagram readback."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from plane_source_cases import CASES, GROUPS, arguments, plan, read
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.distance_sources import source_bytes
from solution_runner.pipelines.solids.spatial_plane_svg import (
    geometry,
    projection,
    template,
)


def prepared(case, gateway):
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


def apply_offline(case, gateway, record):
    return _apply_record(
        gateway,
        record,
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_roundtrips_upload_only_two_corrected_figures_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == (case["task"] in {"526290", "526325"})
    assert len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    for key in ("condition", "source", "criteria"):
        assert section(gateway.context, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_source_drift_stops_before_mock_upload_or_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, key)["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_diagrams_restore_appropriate_names_and_request_mode(case):
    ctx = deepcopy(case["context"])
    for sec in ctx["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["operation"], t["transformation_target_id"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.context["normalized_content"]["assets"]) == (
        2 if case["group"] == "484575" else 1
    )
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_solution_source_is_refused(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = uid = "00000000-0000-4000-8000-000000000001"
    asset["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("526290", "526325"))
@pytest.mark.parametrize("failure", ("svg_drift", "missing_solution", "missing_asset"))
def test_generated_content_drift_or_missing_readback_is_failure(task, failure):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if failure == "svg_drift":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        gateway.omit = (
            "section:solution:1"
            if failure == "missing_solution"
            else "asset:box_distance_solution"
        )
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    if failure == "svg_drift":
        assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("task", ("526290", "526325"))
def test_ratio_diagram_section_and_perpendicular_follow_actual_geometry(task):
    case = next(c for c in CASES if c["task"] == task)
    m = read(case["context"])
    points = geometry(m)
    A, B, C, S = (points[n] for n in "ABCS")
    assert sp.simplify((A - B).norm() - m.q["a"]) == 0
    assert sp.simplify((A - S).norm() - m.q["e"]) == 0
    normal = (points["M"] - points["K"]).cross(points["N"] - points["K"])
    assert sp.simplify(normal.dot(S - A)) == 0
    assert sp.simplify(normal.dot(B - C)) == 0
    assert sp.simplify((points["R"] - points["P"]).cross(normal).norm()) == 0
    assert sp.simplify((points["R"] - points["P"]).norm() - m.answer) == 0
    meta = template()
    meta["vertices"]["A"][0] = meta["vertices"]["S"][0] + 1.35 * (
        meta["vertices"]["A"][0] - meta["vertices"]["S"][0]
    )
    project = projection(points, meta)
    root = ET.fromstring(
        get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])[0][
            "svg_text"
        ]
    )
    ns = "{http://www.w3.org/2000/svg}"
    segment = root.find(ns + 'line[@id="construction-R-P"]')
    for suffix, name in (("1", "R"), ("2", "P")):
        assert tuple(
            float(segment.get(axis + suffix)) for axis in ("x", "y")
        ) == pytest.approx(project(points[name]), abs=1e-5)
    assert root.find(ns + 'g[@id="vertex-T"]') is None
    assert root.find(ns + 'line[@id="construction-H-T"]') is None
    assert len(root.findall(ns + 'line[@id="right-P-0"]')) == 1
    polygon = root.find(ns + 'polygon[@id="section-KNML"]')
    coordinates = [
        tuple(float(v) for v in pair.split(","))
        for pair in polygon.get("points").split()
    ]
    for actual, name in zip(coordinates, ("L", "M", "N", "K"), strict=True):
        assert actual == pytest.approx(project(points[name]), abs=1e-5)
    native = ET.fromstring(source_bytes(meta["source"]))
    originals = [g for g in native.findall(ns + "g") if list(g.iter(ns + "path"))]
    for name, index in meta["glyph_indices"].items():
        if name == "T":
            continue
        group = root.find(ns + 'g[@id="vertex-' + name + '"]')
        assert [p.get("d") for p in group.iter(ns + "path")] == [
            p.get("d") for p in originals[index].iter(ns + "path")
        ]


def test_ratio_perpendicular_beyond_the_apex_extends_the_edge():
    from solution_runner.pipelines.solids.spatial_plane_model import _ratio
    from solution_runner.pipelines.solids.spatial_plane_svg import render

    m = _ratio(("5", "3", "4", "1", "SB", "4", "1", "S"), False)
    assert m.q["small_foot"] == sp.Rational(10, 9)
    root = ET.fromstring(render(m))
    ns = "{http://www.w3.org/2000/svg}"
    extension = root.find(ns + 'line[@id="extension-S-P"]')
    perpendicular = root.find(ns + 'line[@id="construction-R-P"]')
    assert extension is not None
    assert all(
        extension.get(axis + "2") == perpendicular.get(axis + "2")
        for axis in ("x", "y")
    )
