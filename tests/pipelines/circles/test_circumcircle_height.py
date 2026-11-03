"""Both center locations, native aliases, bad saved answers and exact diagrams."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, generated, plan, read
from midpoint_source_cases import replay, section, solution_html
from test_circumcircle_lifecycle import apply_offline, prepared
from test_circumcircle_methods import verify
from test_iso_trapezoid_figures import check_labels
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.circumcircle_height_model import (
    CONDITION_KEY,
    DETAIL,
    DETAIL_KEY,
    INSIDE_SOURCES,
    SOURCE,
)
from solution_runner.pipelines.circles.circumcircle_height_svg import figure_svg
from solution_runner.pipelines.circles.circumcircle_model import read_question
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag

HEIGHTS = [c for c in CASES if c["group"] == "27926"]
OUTSIDE = {
    "27926": 1,
    "53949": 4,
    "53951": 85,
    "53953": 21,
    "53955": 42,
    "53957": 28,
    "53959": 102,
    "53961": 68,
    "53963": 7,
}


def question(a, b, r, location):
    return f"<p>Основания равнобедренной трапеции равны {a} и {b}. Радиус описанной окружности равен {r}. {location}Найдите высоту трапеции.</p>"


def outside(case):
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    m = read(ctx)
    image = str(BeautifulSoup(condition["html"], "html.parser").find("img"))
    condition["html"] = image + question(
        *m.given[:3], "Центр окружности лежит вне трапеции. "
    )
    return ctx


@pytest.mark.parametrize("case", HEIGHTS, ids=lambda c: c["task"])
def test_outside_center_uses_difference_and_preserves_every_parent_equality(case):
    ctx = outside(case)
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert result.answer == str(OUTSIDE[case["task"]])
    assert len(generated(case, ctx)) == 2
    verify(solution_html(result), read(ctx))
    assert ctx == before
    replay(ctx, result.transformations)
    assert section(ctx, "condition")["asset_keys"] == [CONDITION_KEY]
    assert section(ctx, "solution")["asset_keys"] == [DETAIL_KEY]
    assert len(ctx["normalized_content"]["assets"]) == 2
    assert plan(case, ctx).transformations == ()


def xy(line, i):
    return tuple(float(line.get(axis + str(i))) for axis in ("x", "y"))


@pytest.mark.parametrize("case", HEIGHTS, ids=lambda c: c["task"])
@pytest.mark.parametrize("detail", [False, True])
def test_outside_svg_chords_and_radius_lengths_prove_the_different_topology(
    case, detail
):
    model = read(outside(case))
    root = ET.fromstring(figure_svg(model, detail))
    ring = root.find(_tag("circle"))
    center = tuple(float(ring.get(a)) for a in ("cx", "cy"))
    radius = float(ring.get("r"))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    p = {a: xy(lines["side-" + a + b], 1) for a, b in zip("ABCD", "BCDA")}
    scale = radius / float(model.given[2])
    for point in p.values():
        assert math.dist(point, center) == pytest.approx(radius, abs=2e-6)
    assert p["A"][1] == p["B"][1] and p["C"][1] == p["D"][1]
    assert p["C"][1] < p["A"][1] < center[1]
    assert math.dist(p["A"], p["B"]) / scale == pytest.approx(
        float(model.given[0]), abs=2e-6
    )
    assert math.dist(p["C"], p["D"]) / scale == pytest.approx(
        float(model.given[1]), abs=2e-6
    )
    assert (p["A"][1] - p["C"][1]) / scale == pytest.approx(
        OUTSIDE[case["task"]], abs=2e-6
    )
    if detail:
        assert xy(lines["altitude-KO"], 1) == (center[0], p["C"][1])
        assert xy(lines["altitude-KO"], 2) == center
        for name in "ABCD":
            assert (
                xy(lines["radius-O" + name], 1) == center
                and xy(lines["radius-O" + name], 2) == p[name]
            )
            assert lines["radius-O" + name].get("stroke") == "#007EA5"
    assert len(lines) == (9 if detail else 4)
    assert all(e.get("stroke-width") == "0.75" for e in lines.values())
    assert not list(root.iter(_tag("text"))) and not list(root.iter(_tag("image")))
    assert len(root.findall(_tag("g"))) == (7 if detail else 4)
    check_labels(root, [tuple(xy(e, i) for i in (1, 2)) for e in lines.values()])
    original = ET.fromstring(source_bytes(DETAIL if detail else SOURCE))
    original_groups = [
        g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))
    ]
    groups = root.findall(_tag("g"))
    assert [[p.get("d") for p in g.iter(_tag("path"))] for g in groups] == [
        [p.get("d") for p in g.iter(_tag("path"))] for g in original_groups
    ]
    for glyph in groups:
        x, y, w, h = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        x, y = x + dx, y + dy
        near = math.hypot(
            max(x - center[0], 0, center[0] - x - w),
            max(y - center[1], 0, center[1] - y - h),
        )
        far = max(math.dist(center, (bx, by)) for bx in (x, x + w) for by in (y, y + h))
        assert far < radius - 0.5 or near > radius + 0.5
        if detail and glyph is groups[4]:
            assert y + h < center[1]
        if detail and glyph is groups[5]:
            assert y > p["C"][1] and y + h < p["A"][1]


@pytest.mark.parametrize("case", HEIGHTS, ids=lambda c: c["task"])
def test_outside_frozen_fake_roundtrips_materialize_two_roles_only_once(case):
    gateway = OfflineGateway(case)
    gateway.context = outside(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1


def test_alias_is_byte_identical_and_keeps_its_existing_identity():
    assert source_bytes(INSIDE_SOURCES[0]) == source_bytes(INSIDE_SOURCES[1])
    for task in ["53957", "53963"]:
        case = next(c for c in HEIGHTS if c["task"] == task)
        ctx = deepcopy(case["context"])
        replay(ctx, plan(case).transformations)
        asset = next(
            a
            for a in ctx["normalized_content"]["assets"]
            if a["asset_key"] == "image_1"
        )
        assert asset["asset_id"] == INSIDE_SOURCES[1]


@pytest.mark.parametrize("task,expected", [("53961", "124"), ("53963", "17")])
def test_bad_saved_answers_are_recomputed_without_source_edits(task, expected):
    case = next(c for c in HEIGHTS if c["task"] == task)
    before = deepcopy(case["context"])
    assert plan(case).answer == expected and case["context"] == before
    assert BeautifulSoup(section(before, "answer")["html"], "html.parser").get_text(
        strip=True
    ) in {"000", "."}


@pytest.mark.parametrize(
    "a,b,r", [(10, 6, 5), (11, 6, 5), (6, 6, 5), (0, 6, 5), (8, 6, 0)]
)
def test_invalid_or_boundary_chords_are_rejected(a, b, r):
    with pytest.raises(ContentPlanError):
        read_question(question(a, b, r, "Центр окружности лежит внутри трапеции. "))


def test_missing_own_condition_diagram_and_location_is_ambiguous():
    with pytest.raises(ContentPlanError, match="location"):
        read_question(question(8, 6, 5, ""))
    assert (
        read_question(
            question(8, 6, 5, "Центр окружности лежит внутри трапеции. ")
        ).answer
        == 7
    )
    assert (
        read_question(question(8, 6, 5, "Центр окружности лежит вне трапеции. ")).answer
        == 1
    )


@pytest.mark.parametrize(
    "target",
    [
        "asset:" + CONDITION_KEY,
        "asset:" + DETAIL_KEY,
        "section:condition",
        "section:solution",
    ],
)
def test_missing_outside_diagram_or_section_readback_is_failure(target):
    case = HEIGHTS[0]
    gateway = OfflineGateway(case)
    gateway.context = outside(case)
    record = prepared(case, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(target)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("change", ["missing", "duplicate", "key", "hash", "id", "url"])
def test_both_generated_roles_require_exact_metadata(change):
    case = HEIGHTS[0]
    ctx = outside(case)
    assets = list(generated(case, ctx))
    if change == "missing":
        assets.pop()
    elif change == "duplicate":
        assets.append(deepcopy(assets[0]))
    else:
        key = {
            "key": "asset_key",
            "hash": "sha256",
            "id": "source_asset_id",
            "url": "url",
        }[change]
        assets[0][key] = "" if change == "id" else "wrong"
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=tuple(assets))


@pytest.mark.parametrize("drift", ["condition", "svg", "assets"])
def test_frozen_outside_changes_block_before_local_uploads_or_writes(drift):
    case = HEIGHTS[0]
    gateway = OfflineGateway(case)
    gateway.context = outside(case)
    record = prepared(case, gateway)
    if drift == "condition":
        section(gateway.context, "condition")["html"] += "Другие данные"
    elif drift == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes


def test_inside_outside_inside_transitions_keep_two_roles_and_no_duplicate_operations():
    case = HEIGHTS[0]
    ctx = outside(case)
    for location in ["вне", "внутри", "вне"]:
        condition = section(ctx, "condition")
        condition["html"] = (
            condition["html"]
            .replace("внутри", "LOCATION")
            .replace("вне", "LOCATION")
            .replace("LOCATION", location)
        )
        result = plan(case, ctx)
        pairs = [
            (t["transformation_target_id"], t["operation"])
            for t in result.transformations
        ]
        assert len(pairs) == len(set(pairs))
        replay(ctx, result.transformations)
        assert len(ctx["normalized_content"]["assets"]) == 2
        assert plan(case, ctx).transformations == ()
