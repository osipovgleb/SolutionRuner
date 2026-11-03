"""Audited SVG geometry and frozen input failures independently of old answers."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from midpoint_source_cases import section
from rectangle_source_cases import CASES, GROUPS, arguments, plan
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.quadrilaterals.parallelogram.rectangle_sources import (
    source_bytes,
)

SOURCES = {
    "fb7e41fd-a34d-4624-acdd-47fcd236aed9": (True, True),
    "4bcf7ae7-9b12-46c5-a529-fd562577dd45": (False, False),
    "4989651b-d3a3-4011-bfe9-a8696260167b": (False, True),
    "848ff2dd-fce4-4a83-86a8-84bdaaabfe66": (False, True),
}


@pytest.mark.parametrize("source", SOURCES)
def test_reviewed_source_edges_form_the_right_rectangle_and_diagonal(source):
    square, diagonal = SOURCES[source]
    root = ET.fromstring(source_bytes(source))
    edges, diagonals = [], []
    for line in root:
        if line.tag.split("}")[-1] != "line":
            continue
        ends = tuple(
            tuple(float(line.attrib[axis + str(i)]) for axis in ("x", "y"))
            for i in (1, 2)
        )
        (diagonals if line.attrib["stroke"] == "#143B8F" else edges).append(ends)
    assert len(edges) == 4 and len(diagonals) == int(diagonal)
    vertices = {p for edge in edges for p in edge}
    assert len(vertices) == 4
    xs, ys = sorted({p[0] for p in vertices}), sorted({p[1] for p in vertices})
    assert len(xs) == len(ys) == 2
    assert all((p[0] == q[0]) != (p[1] == q[1]) for p, q in edges)
    if square:
        assert xs[1] - xs[0] == pytest.approx(ys[1] - ys[0])
    if diagonal:
        p, q = diagonals[0]
        assert p in vertices and q in vertices and p[0] != q[0] and p[1] != q[1]


@pytest.mark.parametrize("changed", ["condition", "answer"])
def test_frozen_input_drift_blocks_before_local_write(changed):
    case = next(c for c in CASES if c["task"] == "54805")
    gw = OfflineGateway(case)
    rule = GROUPS[case["group"]]["rule"]
    record = _prepared_record(
        gw,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=rule,
        **arguments(case["group"]),
    )
    section(gw.context, changed)["html"] += "<p>Новые данные.</p>"
    result = _apply_record(
        gw, record, content_rule_key=rule, **arguments(case["group"])
    )
    assert result["status"] in {"failed", "blocked"}, result
    assert not gw.writes and not gw.uploads


def test_supported_question_cannot_be_used_with_another_parent_method():
    case = next(c for c in CASES if c["task"] == "27603")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        '<p><img alt="" data-asset-key="image_1" data-asset-id="4bcf7ae7-9b12-46c5-a529-fd562577dd45" src="/assets/4bcf7ae7-9b12-46c5-a529-fd562577dd45"/>Периметр прямоугольника равен 8, а площадь 4. Найдите большую сторону прямоугольника.</p>'
    )
    with pytest.raises(ContentPlanError, match="differs from its rule"):
        plan(case, ctx)
