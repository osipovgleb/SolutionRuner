"""Only a local fake transport exercises frozen preparation and generated readback."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from spatial_distance_cases import CASES, GROUPS, arguments, plan, read
from test_midpoint_area_lifecycle import OfflineGateway
from test_spatial_distance import verify

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.spatial_distance_svg import (
    scene_projection,
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


def custom_box(case, dimensions=(5, 7, 12)):
    ctx = deepcopy(case["context"])
    p, q, r = read(ctx).names
    a, c, h = dimensions
    section(ctx, "condition")["html"] = (
        f"<p>Длины ребер AB, AD и AA_1 прямоугольного параллелепипеда ABCDA_1B_1C_1D_1 равны соответственно {a}, {c} и {h}. Докажите, что расстояние от вершины {q} до прямой {p + r} больше, чем расстояние от вершины {p} до прямой {q + r}. Найдите расстояние от вершины {p} до прямой {q + r}.</p>"
    )
    return ctx


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_offline_roundtrip_keeps_exact_figures_without_uploads(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert (
        gateway.context["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    for key in ("condition", "source", "criteria"):
        assert section(gateway.context, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("change", ("condition", "criteria", "solution"))
def test_frozen_input_drift_blocks_before_mock_write(case, change):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, change)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ("parent_asset_id", "parent_solution_html", "parent_solution_assets")
)
def test_complete_parent_method_pins(case, field):
    with pytest.raises(ContentPlanError):
        plan(case, **{field: () if field == "parent_solution_assets" else "changed"})


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_foreign_source_asset_is_refused(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    uid = "00000000-0000-4000-8000-000000000001"
    asset["asset_id"] = uid
    asset["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("index", (3, 4))
def test_changed_numbers_prepare_actual_altitude_and_resume(index):
    case = CASES[index]
    ctx = custom_box(case)
    handler = get_handler(GROUPS[case["group"]]["rule"])
    drawings = handler.diagram_specs(ctx)
    assert len(drawings) == 1 and drawings[0]["asset_key"] == "box_distance_solution"
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    root = ET.fromstring(drawings[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert {n.text for n in root.findall("s:text", ns)} == {"5", "7", "12"}
    assert len(root.findall('s:g[@id="vertex-E"]', ns)) == 1
    _vertices, foot, _marker = scene_projection(read(ctx), template())
    point = root.find('s:line[@id="altitude-' + read(ctx).names[0] + '-E"]', ns)
    assert float(point.get("x2")) == pytest.approx(foot[0], abs=1e-5)
    assert float(point.get("y2")) == pytest.approx(foot[1], abs=1e-5)
    assert len(root.findall('s:line[@id="right-angle-0"]', ns)) == 1
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert not plan(case, updated).transformations
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 1 and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 1 and len(gateway.writes) == 1


@pytest.mark.parametrize("failure", ("svg_drift", "missing_readback"))
def test_generated_altitude_drift_or_missing_readback_is_not_success(failure):
    case = CASES[3]
    ctx = custom_box(case)
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    if failure == "svg_drift":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        gateway.omit = "section:solution:1"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    if failure == "svg_drift":
        assert not gateway.uploads and not gateway.writes


def test_swapped_pyramid_diagram_roles_are_refused():
    case = CASES[0]
    ctx = deepcopy(case["context"])
    soup = BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
    imgs = soup.find_all("img")
    a, b = (i["data-asset-id"] for i in imgs)
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(a, "SWAP").replace(b, a).replace("SWAP", b)
    for asset in ctx["normalized_content"]["assets"]:
        uid = b if asset["asset_id"] == a else a
        asset["asset_id"] = uid
        asset["url"] = "/assets/" + uid
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "case,key",
    ((CASES[3], "box_distance_condition"), (CASES[0], "box_distance_solution")),
)
def test_generated_keys_cannot_bypass_proof_figure_roles(case, key):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = (
            sec["html"]
            .replace("asset:image_1", "asset:" + key)
            .replace('data-asset-key="image_1"', 'data-asset-key="' + key + '"')
        )
        sec["asset_keys"] = [key if v == "image_1" else v for v in sec["asset_keys"]]
    asset["asset_key"] = key
    asset["transformation_target_id"] = "asset:" + key
    if key == "box_distance_condition":
        sol, condition = section(ctx, "solution"), section(ctx, "condition")
        soup = BeautifulSoup(sol["html"], "html.parser")
        img = soup.find("img")
        html = str(img)
        img.decompose()
        sol["html"] = str(soup)
        sol["asset_keys"].remove(key)
        condition["html"] = html + condition["html"]
        condition["asset_keys"].append(key)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "blocked" and record["transformations"] == []
    assert not gateway.uploads and not gateway.writes
