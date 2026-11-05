"""Only local fake transport verifies role guards, frozen inputs and generated figures."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from metric_source_cases import CASES, GROUPS, arguments, plan
from midpoint_source_cases import section
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.distance_sources import source_bytes
from solution_runner.pipelines.solids.spatial_metric_svg import template


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
def test_all_offline_roundtrips_materialize_only_wrong_hex_diagram_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert (
        len(gateway.uploads) == (case["task"] == "507766") and len(gateway.writes) == 1
    )
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert (
        len(gateway.uploads) == (case["task"] == "507766") and len(gateway.writes) == 1
    )
    for key in ("condition", "criteria", "source"):
        assert section(gateway.context, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_source_drift_is_refused_before_mock_upload_or_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, key)["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_solution_figure_is_refused(case):
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_id"]
    uid = "00000000-0000-4000-8000-000000000001"
    a["asset_id"] = uid
    a["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_native_diagrams_restore_actual_names_without_duplicate_targets(case):
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
        2 if case["group"] == "503000" else 1
    )
    assert len(gateway.uploads) == (case["task"] == "507766")
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize("failure", ("svg_drift", "missing_solution", "missing_asset"))
def test_generated_hex_content_drift_or_missing_readback_is_not_success(failure):
    case = next(c for c in CASES if c["task"] == "507766")
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


def test_hex_diagram_uses_the_requested_SF_altitude_and_preserves_native_frame():
    case = next(c for c in CASES if c["task"] == "507766")
    handler = get_handler(GROUPS[case["group"]]["rule"])
    drawing = handler.diagram_specs(case["context"])[0]
    root = ET.fromstring(drawing["svg_text"])
    meta = template()
    native = ET.fromstring(source_bytes(meta["source"]))
    ns = "{http://www.w3.org/2000/svg}"
    black = lambda r: [
        ET.tostring(n)
        for n in list(r)
        if n.tag == ns + "line" and n.get("stroke") == "#000000"
    ]
    assert black(root) == black(native)
    line = root.find(ns + 'line[@id="altitude-C-M"]')
    S, F = (meta["vertices"][n] for n in ("S", "F"))
    M = ((S[0] + F[0]) / 2, (S[1] + F[1]) / 2)
    assert (float(line.get("x2")), float(line.get("y2"))) == pytest.approx(M, abs=1e-5)
    assert line.get("stroke-dasharray") == "7.5,3"
    assert root.find(ns + 'line[@id="altitude-A-E"]') is not None
    assert root.find(ns + 'line[@id="altitude-A-C"]') is None
    assert root.find(ns + 'line[@id="altitude-C-F"]') is not None
    originals = [g for g in native.findall(ns + "g") if list(g.iter(ns + "path"))]
    for name, index in meta["glyph_indices"].items():
        group = root.find(ns + 'g[@id="vertex-' + name + '"]')
        assert [p.get("d") for p in group.iter(ns + "path")] == [
            p.get("d") for p in originals[index].iter(ns + "path")
        ]


@pytest.mark.parametrize("edge,fraction", (("3", 7 / 9), (r"\frac{6}{5}", -7 / 18)))
def test_other_hex_triangle_uses_actual_foot_including_line_extension(edge, fraction):
    from metric_source_cases import read
    from midpoint_source_cases import solution_html
    from test_spatial_metrics import verify

    case = next(c for c in CASES if c["task"] == "507763")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        '<p>В правильной шестиугольной пирамиде SABCDEF стороны основания равны 1, а боковые рёбра равны <span data-inline-latex="'
        + edge
        + '"></span>. Докажите, что прямые SE и AC перпендикулярны. Найдите расстояние от точки D до прямой SA.</p>'
    )
    result = plan(case, ctx)
    m = read(ctx)
    assert verify(solution_html(result), m) == m.answer
    drawing = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)[0]
    root = ET.fromstring(drawing["svg_text"])
    ns = "{http://www.w3.org/2000/svg}"
    S, A = (template()["vertices"][k] for k in ("S", "A"))
    M = tuple(S[i] + fraction * (A[i] - S[i]) for i in (0, 1))
    segment = root.find(ns + 'line[@id="altitude-D-M"]')
    assert (float(segment.get("x2")), float(segment.get("y2"))) == pytest.approx(
        M, abs=1e-5
    )
    assert (root.find(ns + 'line[@id="altitude-M-S"]') is not None) == (fraction < 0)
