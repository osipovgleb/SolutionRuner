"""Verify complete line-angle geometry, proof equalities and frozen content locally."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from line_angle_source_cases import CASES, arguments, plan, read, saved_answer
from midpoint_source_cases import replay, section, solution_html
from test_distance_preparation import verify
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids.box_line_angle_model import segments
from solution_runner.pipelines.solids.line_angle_parent import diagram_specs
from solution_runner.pipelines.solids.line_angle_sources import (
    RULE,
    SOURCE,
    source_bytes,
)


def condition(lines, lengths=(2, 3, 4)):
    return (
        "<p>В прямоугольном параллелепипеде "
        "ABCDA_1B_1C_1D_1 известны длины рёбер "
        f"AB={lengths[0]}, AD={lengths[1]}, AA_1={lengths[2]}. "
        f"Найдите синус угла между прямыми {lines[0]} и {lines[1]}.</p>"
    )


def vector(segment, squares):
    a, b = c.endpoints(segment)
    return sp.Matrix(
        [(y - x) * sp.sqrt(v) for x, y, v in zip(c.VERTICES[a], c.VERTICES[b], squares)]
    )


def sine(first, second, squares):
    u, v = vector(first, squares), vector(second, squares)
    return sp.simplify(sp.sqrt(u.cross(v).dot(u.cross(v)) / (u.dot(u) * v.dot(v))))


def verify_proof(result, model):
    soup = BeautifulSoup(solution_html(result), "html.parser")
    for tag in soup.select("[data-inline-latex]"):

        def replace(match):
            a, b, d = re.findall(c.VERTEX, match[1])
            return "(" + sp.latex(sine(b + a, b + d, model.squares)) + ")"

        tag["data-inline-latex"] = re.sub(
            r"\\sin\s+((?:" + c.VERTEX + r"){3})", replace, tag["data-inline-latex"]
        )
    verify(str(soup), model)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_native_answers_parent_method_exact_source_reuse_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    result = plan(case, ctx)
    model = read(case)
    assert ctx == before
    assert (
        sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    assert model.answer == sine(*model.lines, model.squares)
    verify_proof(result, model)
    assert not diagram_specs(ctx)
    assert [SOURCE] == [
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    ] or not ctx["normalized_content"]["assets"]
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    section(ctx, "answer")["html"] = "<p>999</p>"
    assert plan(case, ctx).answer == result.answer


FACES = [
    (a + b, axis)
    for a, b in itertools.combinations(c.VERTICES, 2)
    if len(c.axes(a + b)) == 2
    for axis in c.axes(a + b)
]


@pytest.mark.parametrize("diagonal,axis", FACES)
def test_every_face_diagonal_and_parallel_edge_plane_has_actual_proof_and_figure(
    diagonal, axis
):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    edge = next(
        a + b
        for a, b in itertools.combinations(c.VERTICES, 2)
        if c.axes(a + b) == (axis,)
    )
    section(ctx, "condition")["html"] = condition((edge, diagonal))
    result = plan(case, ctx)
    model = read({"context": ctx})
    assert model.answer == sine(edge, diagonal, model.squares)
    verify_proof(result, model)
    specs = diagram_specs(ctx)
    assert bool(specs) == (segments(model) != (("A", "C"), ("A_1", "C_1")))
    if specs:
        import xml.etree.ElementTree as ET

        from solution_runner.pipelines.triangles.right.construction_svg import _tag

        root = ET.fromstring(specs[0]["svg_text"])
        assert {
            tuple(node.attrib["id"].removeprefix("helper-").split("-"))
            for node in root.findall(_tag("line"))
            if node.attrib["id"].startswith("helper-")
        } == set(segments(model))
        assert (
            len(
                [
                    n
                    for n in root.findall(_tag("line"))
                    if n.get("id", "").startswith("wire-")
                ]
            )
            == 12
        )
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    reverse = deepcopy(case["context"])
    a, b = c.endpoints(diagonal)
    x, y = c.endpoints(edge)
    section(reverse, "condition")["html"] = condition((b + a, y + x))
    assert plan(case, reverse).answer == result.answer


@pytest.mark.parametrize(
    "bad",
    [
        (("AB", "AC"), (0, 3, 4)),
        (("AB", "AC"), (-2, 3, 4)),
        (("AB", "AC"), ("\\sqrt{-1}", 3, 4)),
        (("AA_1", "AC"), (2, 3, 4)),
        (("AB", "AC_1"), (2, 3, 4)),
        (("AB", "CD"), (2, 3, 4)),
        (("AA", "AC"), (2, 3, 4)),
    ],
)
def test_nonexistent_or_different_geometry_rejected(bad):
    ctx = deepcopy(CASES[0]["context"])
    section(ctx, "condition")["html"] = condition(*bad)
    with pytest.raises(ContentPlanError):
        plan(CASES[0], ctx)


@pytest.mark.parametrize(
    "field", ["url", "source", "owner", "unused", "instructions", "generated"]
)
def test_unknown_or_inconsistent_figure_and_instructions_rejected(field):
    ctx = deepcopy(CASES[0]["context"])
    asset = ctx["normalized_content"]["assets"][0]
    if field == "url":
        asset["url"] = "https://example.com/foreign.svg"
    elif field == "source":
        asset["asset_id"] = "foreign"
    elif field == "owner":
        sol = section(ctx, "solution")
        image = BeautifulSoup(sol["html"], "html.parser").find("img")
        sol["html"] = "<p>Нет рисунка</p>"
        sol["asset_keys"] = []
        section(ctx, "condition")["html"] += str(image)
        section(ctx, "condition")["asset_keys"] = ["image_1"]
    elif field == "unused":
        section(ctx, "solution")["html"] = "<p>Без рисунка</p>"
        section(ctx, "solution")["asset_keys"] = []
    elif field == "instructions":
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    if field == "generated":
        with pytest.raises(ContentPlanError):
            plan(CASES[0], ctx, generated_solution_assets=({"asset_key": "foreign"},))
    else:
        with pytest.raises(ContentPlanError):
            plan(CASES[0], ctx)


def test_profile_parent_and_source_pins():
    handler = get_handler(RULE)
    handler.validate()
    profile = get_group_profile("318474")
    assert profile.source_group_id == "5d238889-2697-4a55-8c31-700eef058a4e"
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    assert source_bytes().startswith(b"<?xml")
    for override in [
        {"parent_asset_id": "foreign"},
        {
            "parent_solution_html": arguments("318474")["parent_solution_html"]
            + "<p>Другой метод</p>"
        },
        {"parent_solution_assets": ()},
    ]:
        with pytest.raises(ContentPlanError):
            plan(CASES[0], **override)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["task"])
def test_native_frozen_roundtrip_restores_only_solution_figure_without_upload(case):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=RULE,
        **arguments("318474"),
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(
        gateway, record, content_rule_key=RULE, **arguments("318474")
    )
    assert (
        result["status"] == "applied"
        and not gateway.uploads
        and len(gateway.writes) == 1
    )
    assert (
        _apply_record(gateway, record, content_rule_key=RULE, **arguments("318474"))[
            "status"
        ]
        == "already_complete"
    )


def spatial_case():
    case = deepcopy(CASES[-1])
    section(case["context"], "condition")["html"] = condition(("CD", "BD"))
    return case


def prepared(case, gateway):
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=RULE,
        **arguments("318474"),
    )


def apply_offline(gateway, record):
    return _apply_record(gateway, record, content_rule_key=RULE, **arguments("318474"))


def test_generated_face_diagonals_freeze_materialize_once_and_resume():
    case = spatial_case()
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and len(record["generated_diagrams"]) == 1
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert apply_offline(gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert section(gateway.context, "condition") == section(
        case["context"], "condition"
    )


@pytest.mark.parametrize(
    "target", ["asset:box_line_angle_solution", "section:solution"]
)
def test_generated_picture_and_solution_readback_must_exist(target):
    case = spatial_case()
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_frozen_drift_never_uploads_or_writes(drift):
    case = spatial_case()
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if drift in {"svg", "sha"}:
        record["generated_diagrams"][0]["svg_text" if drift == "svg" else "sha256"] += (
            "changed"
        )
    else:
        section(gateway.context, drift)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
