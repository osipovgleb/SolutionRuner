"""Midpoint geometry, both source figures and frozen lifecycle for group 27845."""

import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from perimeter_source_cases import ARGUMENTS, CASES, DATA, plan
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_model import (
    PERIMETER,
    read_question,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_sources import (
    PERIMETER_CONDITION,
    PERIMETER_FIGURE,
    source_bytes,
)

DIAGONALS = {"27845": (4, 5), "50931": (6, 2), "50933": (57, 8), "50935": (72, 35)}


def perimeter(first, second, angle, s, t):
    theta = math.radians(angle)
    x = first * s
    b = (x - second * t * math.cos(theta), -second * t * math.sin(theta))
    d = (x + second * (1 - t) * math.cos(theta), second * (1 - t) * math.sin(theta))
    outer = [(0, 0), b, (first, 0), d]
    midpoints = [
        tuple((p[i] + q[i]) / 2 for i in range(2))
        for p, q in zip(outer, outer[1:] + outer[:1])
    ]
    return sum(
        math.dist(p, q) for p, q in zip(midpoints, midpoints[1:] + midpoints[:1])
    )


def verify(html, first, second):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        text = tag["data-inline-latex"]
        for name, value in [
            ("AC", first),
            ("CA", first),
            ("BD", second),
            ("DB", second),
            ("P", first + second),
        ]:
            text = text.replace(name, "(" + str(value) + ")")
        values = [float(TrigonometricParser(p).parse().value) for p in text.split("=")]
        assert len(values) > 1 and all(
            math.isclose(v, values[0], abs_tol=1e-10) for v in values
        ), text


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_and_every_parent_formula_follow_independent_midpoint_geometry(
    case,
):
    ctx = case["context"]
    model = read_question(section(ctx, "condition")["html"], PERIMETER_CONDITION)
    first, second = DIAGONALS[case["task"]]
    assert model.diagonals == (first, second)
    result = plan(ctx)
    for angle in (15, 45, 90, 130, 170):
        for s, t in ((0.2, 0.3), (0.5, 0.5), (0.9, 0.1)):
            assert perimeter(first, second, angle, s, t) == pytest.approx(
                float(result.answer)
            )
    saved = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text(
        strip=True
    )
    assert Fraction(saved) == Fraction(result.answer) == first + second
    html = solution_html(result)
    verify(html, first, second)
    methods = BeautifulSoup(html, "html.parser").select("section")
    assert len(methods) == 1 and methods[0]["data-solution-title"] == "Решение"
    assert len(methods[0].select("center [data-inline-latex]")) == 7
    assert [im["data-asset-id"] for im in methods[0].select("img")] == [
        PERIMETER_FIGURE
    ]
    assert get_handler(PERIMETER).diagram_specs(ctx) == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_conditions_immutable_missing_solution_restored_and_replay_empty(
    case,
):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(ctx)
    assert ctx == before and result.answer == plan(case["context"]).answer
    if case["task"] in {"50933", "50935"}:
        asset_changes = [
            t
            for t in result.transformations
            if t["transformation_target_id"].startswith("asset:")
        ]
        assert len(asset_changes) == 1 and asset_changes[0]["operation"] == "add"
        assert asset_changes[0]["value"]["asset_id"] == PERIMETER_FIGURE
    replay(ctx, result.transformations)
    assert section(ctx, "condition") == section(before, "condition")
    assert plan(ctx).transformations == ()
    assert len(ctx["normalized_content"]["assets"]) == 2


def test_registered_source_binding_uses_the_actual_parent_and_shared_preparer():
    profile, handler = get_group_profile("27845"), get_handler(PERIMETER)
    assert profile.source_group_id == DATA["groups"][0]["group_uuid"]
    assert profile.existing_solution_policy == "rewrite"
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )
    assert handler.target.endswith("midpoint_parent:prepare")
    handler.validate()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_local_frozen_roundtrips_restore_existing_figures_without_upload_and_resume(
    case,
):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=PERIMETER,
        **ARGUMENTS,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, content_rule_key=PERIMETER, **ARGUMENTS)
    assert result["status"] == "applied", result
    assert not gateway.uploads and len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, content_rule_key=PERIMETER, **ARGUMENTS)[
            "status"
        ]
        == "already_complete"
    )
    assert (
        len(gateway.writes) == 1
        and len(gateway.context["normalized_content"]["assets"]) == 2
    )


@pytest.mark.parametrize(
    "change",
    [
        "instruction",
        "new_fact",
        "negative",
        "zero",
        "missing_midpoint",
        "ambiguous",
        "foreign_asset",
        "wrong_owner",
        "parent",
        "parent_asset",
        "parent_solution_asset",
    ],
)
def test_unreviewed_conditions_parent_methods_and_figure_ownership_fail_closed(change):
    ctx = deepcopy(CASES[0]["context"])
    overrides = {}
    condition = section(ctx, "condition")
    if change == "instruction":
        condition["html"] += "<p>Округлите ответ до целых.</p>"
    elif change == "new_fact":
        condition["html"] += "<p>Угол A прямой.</p>"
    elif change in {"negative", "zero"}:
        condition["html"] = condition["html"].replace(
            "равны\u202f4", "равны\u202f-4" if change == "negative" else "равны\u202f0"
        )
    elif change == "missing_midpoint":
        condition["html"] = condition["html"].replace("се\xadре\xadди\xadны", "точки")
    elif change == "ambiguous":
        condition["html"] += '<p style="display:none">Другие данные</p>'
    elif change == "foreign_asset":
        ctx["normalized_content"]["assets"][1]["asset_id"] = "foreign"
    elif change == "wrong_owner":
        condition["asset_keys"] = []
    elif change == "parent":
        overrides["parent_solution_html"] = (
            ARGUMENTS["parent_solution_html"] + "<p>Новый способ.</p>"
        )
    elif change == "parent_asset":
        overrides["parent_asset_id"] = PERIMETER_FIGURE
    else:
        overrides["parent_solution_assets"] = ()
    with pytest.raises(ContentPlanError):
        plan(ctx, **overrides)


@pytest.mark.parametrize(
    "first,second,expected",
    [("3,5", "2,25", "5,75"), ("1{,}125", "2{,}875", "4"), ("5", "5", "10")],
)
def test_exact_decimals_equal_diagonals_and_unlabelled_order(first, second, expected):
    ctx = deepcopy(CASES[0]["context"])
    html = f"<p>Диагонали четырёхугольника равны {first} и {second}. Найдите периметр четырёхугольника, вершинами которого являются середины сторон данного четырёхугольника.</p>"
    # The source condition picture remains part of the normalized question.
    image = str(BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img)
    section(ctx, "condition")["html"] = image + html
    result = plan(ctx)
    assert result.answer == expected
    a, b = [float(v.replace("{,}", ".").replace(",", ".")) for v in (first, second)]
    verify(solution_html(result), a, b)


def test_reviewed_source_solution_lines_join_actual_side_midpoints():
    root = ET.fromstring(source_bytes(PERIMETER_FIGURE))
    cyan = [line for line in root if line.attrib.get("stroke") == "#007EA5"]
    assert len(cyan) == 4
    outer = [(14.703, 85.784), (38.254, 15.194), (113.4, 26.18), (144.239, 85.784)]
    mids = [
        tuple((p[i] + q[i]) / 2 for i in range(2))
        for p, q in zip(outer, outer[1:] + outer[:1])
    ]
    edges = set()
    for line in cyan:
        ends = [
            tuple(float(line.attrib[a + str(i)]) for a in ("x", "y")) for i in (1, 2)
        ]
        matched = [
            next(i for i, m in enumerate(mids) if math.dist(m, end) < 0.005)
            for end in ends
        ]
        assert (matched[0] - matched[1]) % 4 in {1, 3}
        edges.add(tuple(sorted(matched)))
    assert len(edges) == 4
    assert source_bytes(PERIMETER_CONDITION) != source_bytes(PERIMETER_FIGURE)


@pytest.mark.parametrize("task", ["50933", "50935"])
def test_missing_solution_figure_readback_is_a_failure(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit="asset:image_2")
    child = {"problem_id": case["context"]["problem_id"], "source_problem_id": task}
    record = _prepared_record(gateway, child, content_rule_key=PERIMETER, **ARGUMENTS)
    result = _apply_record(gateway, record, content_rule_key=PERIMETER, **ARGUMENTS)
    assert result["status"] == "failed", result


@pytest.mark.parametrize("changed", ["condition", "answer"])
def test_frozen_input_drift_blocks_before_local_write(changed):
    case = CASES[2]
    gateway = OfflineGateway(case)
    child = {
        "problem_id": case["context"]["problem_id"],
        "source_problem_id": case["task"],
    }
    record = _prepared_record(gateway, child, content_rule_key=PERIMETER, **ARGUMENTS)
    section(gateway.context, changed)["html"] += "<p>Другие данные.</p>"
    result = _apply_record(gateway, record, content_rule_key=PERIMETER, **ARGUMENTS)
    assert result["status"] in {"failed", "blocked"}, result
    assert not gateway.uploads and not gateway.writes
