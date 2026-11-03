"""Check all parent methods against independent coordinates and public frozen replay."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_isosceles_side_altitude_proofs import angular_values
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay
from vertex_altitude_cases import CASES, GROUPS, PARENTS, parent_html, plan, section

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.vertex_altitude_figures import (
    ACUTE,
    OBTUSE,
    selection,
    source_bytes,
)


def check_rows(html, m):
    if m.mode == "side_height":
        side = TrigonometricParser(m.side_raw).parse().value
        height = TrigonometricParser(m.height_raw).parse().value
        x = sp.sqrt(sp.simplify(side**2 - height**2))
    else:
        gamma = sp.pi * m.apex_angle / 180
        sine = sp.sin(gamma)
        side = (
            TrigonometricParser(m.side_raw).parse().value
            if m.side_raw is not None
            else sp.simplify(TrigonometricParser(m.height_raw).parse().value / sine)
        )
        height = sp.simplify(side * sine)
        x = sp.simplify(side * sp.cos(gamma))
    points = {
        m.apex: sp.Matrix([0, 0]),
        m.vertex: sp.Matrix([x, height]),
        m.other_base_vertex: sp.Matrix([side, 0]),
        "H": sp.Matrix([x, 0]),
    }
    area = (
        abs(sp.det(sp.Matrix.hstack(points[m.vertex], points[m.other_base_vertex]))) / 2
    )
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def trig(match):
            sine, cosine = angular_values(points, match[2])
            value = (
                sine
                if match[1] == "sin"
                else cosine
                if match[1] == "cos"
                else sine / cosine
            )
            return "(" + sp.latex(sp.simplify(value)) + ")"

        text = re.sub(r"\\(sin|cos|tg)\s*\\angle\s*([ABCH]{1,3})", trig, raw)

        def numeric(match):
            angle = sp.Rational(match[2]) * sp.pi / 180
            return (
                "("
                + sp.latex(
                    sp.simplify(sp.sin(angle) if match[1] == "sin" else sp.cos(angle))
                )
                + ")"
            )

        text = re.sub(r"\\(sin|cos)\s*(\d+)\^\{\\circ\}", numeric, text)

        def angle(match):
            _, cosine = angular_values(points, match[1])
            return "(" + sp.latex(sp.simplify(180 * sp.acos(cosine) / sp.pi)) + ")"

        text = re.sub(r"\\angle\s*([ABCH]{1,3})", angle, text).replace(r"^{\circ}", "")

        def length(match):
            return (
                "("
                + sp.latex(
                    sp.simplify((points[match[0][0]] - points[match[0][1]]).norm())
                )
                + ")"
            )

        text = re.sub(r"[ABCH]{2}", length, text)
        text = re.sub(r"\bS\b", lambda _: "(" + sp.latex(area) + ")", text)
        values = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_public_answers_all_methods_and_immutable_replay(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    untouched = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == untouched
    expected = sp.Rational(
        BeautifulSoup(section(before, "answer")["html"], "html.parser")
        .get_text()
        .replace(",", ".")
    )
    assert sp.Rational(result.answer.replace(",", ".")) == expected
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, m)
    titles = [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ]
    assert (
        titles
        == {
            "27795": ["Решение", "Альтернативное решение."],
            "27796": [
                "Решение",
                "Приведем другое решение",
                "Приведем еще одно решение",
            ],
            "27797": ["Решение"],
            "27798": ["Решение"],
        }[case["group"]]
    )
    assert (
        plan(case, ctx).transformations == ()
        and section(ctx, "condition")["html"] == section(before, "condition")["html"]
    )
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    assert (
        profile.existing_solution_policy == "rewrite"
        and profile.source_group_id == GROUPS[case["group"]]["group_uuid"]
    )
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_statements_are_rejected(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + extra + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_are_not_ignored(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")


def synthetic(frame, angle, mode):
    p, q, r = frame
    group = (
        "27797"
        if mode == "height_angle"
        else "27796"
        if mode == "side_height"
        else "27798"
        if angle > 90
        else "27795"
    )
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    side, height = {
        30: ("4", "2"),
        45: (r"2\sqrt{2}", "2"),
        60: (r"2\sqrt{3}", "3"),
        90: ("4", "4"),
        120: (r"2\sqrt{3}", "3"),
        135: (r"2\sqrt{2}", "2"),
    }[angle]
    if mode == "height_angle" and angle in {45, 60, 120, 135}:
        height = r"5\sqrt{2}" if angle in {45, 135} else r"5\sqrt{3}"
    equal = p + r + "=" + q + r
    if mode == "side_angle":
        given = equal + "=" + side + f", угол {r} равен {angle}°"
        request = "высоту " + p + "H."
        prefix = "В треугольнике ABC "
    elif mode == "height_angle":
        given = equal + f", высота {p}H равна {height}, угол {r} равен {angle}°"
        request = p + r + "."
        prefix = "В треугольнике ABC "
    else:
        given = equal + f"={side}, высота {p}H равна {height}"
        request = f"угол {r}. Ответ дайте в градусах."
        prefix = "В остроугольном треугольнике ABC известно, что "
    section(ctx, "condition")["html"] = (
        f"<p>{image}{prefix}{given}. Найдите {request}</p>"
    )
    return case, ctx


@pytest.mark.parametrize("task", ["4805", "48913", "48919", "4809"])
def test_native_offline_frozen_readback_reuses_existing_source(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    group = case["group"]
    source = OBTUSE if group == "27798" else ACUTE
    rule = GROUPS[group]["rule"]
    kwargs = {"parent_solution_html": parent_html(group)}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "applied"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, source, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("kind", ["zero", "remap", "lost_condition"])
def test_generated_uuid_and_authoritative_offline_readback(kind):
    case, ctx = synthetic(
        ("A", "B", "C") if kind != "remap" else ("C", "A", "B"),
        90 if kind != "remap" else 135,
        "side_angle",
    )
    case = {**case, "context": ctx}
    group = case["group"]
    gateway = OfflineGateway(case, omit_condition_write=kind == "lost_condition")
    source = OBTUSE if group == "27798" else ACUTE
    rule = GROUPS[group]["rule"]
    kwargs = {"parent_solution_html": parent_html(group)}
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == ("failed" if kind == "lost_condition" else "applied"), (
        result
    )
    if kind != "lost_condition":
        assert (
            _apply_record(gateway, record, source, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("kind", ["extra", "url", "reference", "unknown"])
def test_unreviewed_assets_are_rejected(kind):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append(
            {"asset_key": "image_2", "asset_id": "other"}
        )
    elif kind == "url":
        asset["url"] = "/assets/other"
    elif kind == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            ACUTE, "other"
        )
    else:
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_missing_acute_assumption_cannot_select_one_of_two_vertex_angles():
    case = PARENTS["27796"]
    ctx = deepcopy(case["context"])
    html = section(ctx, "condition")["html"]
    image = BeautifulSoup(html, "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC AC=BC=6, высота AH равна 3. Найдите угол C. Ответ дайте в градусах.</p>"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "text",
    [
        "В остроугольном треугольнике ABC известно, что AC=BC=6, высота AH равна 6. Найдите угол C. Ответ дайте в градусах.",
        "В треугольнике ABC AC=BC=6, угол A равен 30°. Найдите высоту AH.",
        "В треугольнике ABC AC=BC=6, угол C равен 30°. Найдите высоту CH.",
    ],
)
def test_inconsistent_side_altitude_questions_fail_closed(text):
    case = PARENTS["27795"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [ACUTE, OBTUSE])
def test_audited_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


def test_inverse_can_request_the_other_equal_side():
    case, ctx = synthetic(("A", "B", "C"), 30, "height_angle")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "Найдите AC.", "Найдите BC."
    )
    result = plan(case, ctx)
    assert result.answer == "4"
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()


def test_altitude_length_can_precede_its_explicit_definition():
    case = PARENTS["27796"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В остроугольном треугольнике ABC известно, что AC=BC=6, HA=3, AH — высота. Найдите угол C. Ответ дайте в градусах.</p>"
    )
    result = plan(case, ctx)
    assert result.answer == "30"
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()
