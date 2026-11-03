"""Exercise both requests of the mixed bisector group through the shared runner."""

import itertools
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from named_bisector_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_simple_angle_preparation import check_rows
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.general.simple_angle_figures import (
    NAMED_BISECTOR,
    selection,
    source_bytes,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_requests_preserve_parent_method_and_source(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    condition = section(ctx, "condition")["html"]
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], selection(ctx)[0])
    assert section(ctx, "condition")["html"] == condition
    assert plan(case, ctx).transformations == ()
    assert get_handler(GROUPS["681454"]["rule"]).diagram_specs(ctx) == ()
    if case["task"] == "704521":
        assert (
            r"\angle ADB=180^{\circ}-\angle BAD-\angle ABD"
            in section(ctx, "solution")["html"]
        )


def synthetic(mode, frame, conditional):
    case = PARENTS["681454"]
    ctx = deepcopy(case["context"])
    a, b, c = frame
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    target = a + b + "D" if mode == "bisector_base" else a + "D" + b
    if conditional:
        text = f"В треугольнике ABC проведена биссектриса {a}D. Найдите угол {target}, если угол {b}{a}D равен 28° и угол {a}{c}{b} равен 50°."
    else:
        text = f"В треугольнике ABC угол {c} равен 50°, {a}D — биссектриса, угол {b}{a}D равен 28°. Найдите величину угла {target}. Ответ дайте в градусах."
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    return case, ctx


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("mode", ["bisector_base", "bisector_external"])
@pytest.mark.parametrize("conditional", [False, True])
def test_both_named_requests_all_frames_and_conditional_wording(
    frame, mode, conditional
):
    case, ctx = synthetic(mode, frame, conditional)
    result = plan(case, ctx)
    assert result.answer == ("74" if mode == "bisector_base" else "78")
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_no_additional_facts_are_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,frame,lost",
    [
        ("bisector_base", "ABC", False),
        ("bisector_external", "ABC", False),
        ("bisector_external", "CAB", False),
        ("bisector_external", "CAB", True),
    ],
)
def test_local_frozen_roundtrip_reuses_or_relabels_source(mode, frame, lost):
    case, ctx = synthetic(mode, frame, True)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS["681454"]["rule"]
    kwargs = {"parent_solution_html": parent_html("681454")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        NAMED_BISECTOR,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, NAMED_BISECTOR, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, NAMED_BISECTOR, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize(
    "old,new",
    [
        ("проведена биссектриса AD", "проведена медиана AD"),
        ("угол BAD", "угол ABD"),
        ("угол ACB", "угол CAB"),
        ("28°", "90°"),
    ],
)
def test_contradictory_or_unknown_named_roles_fail_closed(old, new):
    case, ctx = synthetic("bisector_base", "ABC", True)
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_changed_parent_and_source_identity_are_rejected():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=parent_html("681454") + "<p>Другой способ.</p>")
    assert source_bytes(NAMED_BISECTOR).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize("kind", ["extra", "unknown", "url", "reference"])
def test_unreviewed_assets_fail_closed(kind):
    case, ctx = synthetic("bisector_base", "ABC", True)
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif kind == "unknown":
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    elif kind == "url":
        asset["url"] = "/assets/other"
    else:
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            asset["asset_id"], "other"
        )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
