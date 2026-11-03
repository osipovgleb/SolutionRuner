"""Check base-altitude methods with independent point geometry and frozen replay."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from base_height_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from bs4 import BeautifulSoup
from test_isosceles_side_altitude_proofs import angular_values
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.base_height_figures import (
    SOURCE,
    selection,
)


def check_rows(html, m):
    first = TrigonometricParser(m.first_raw).parse().value
    if m.mode == "base_height_to_angle":
        base = first
        height = TrigonometricParser(m.second_raw).parse().value
    elif m.mode == "side_to_height":
        base = first
        height = sp.sqrt(first**2 - (base / 2) ** 2)
    else:
        height = first
        base = sp.simplify(2 * height / sp.sqrt(3))
    p, q = m.base_vertices
    points = {
        p: sp.Matrix([-base / 2, 0]),
        q: sp.Matrix([base / 2, 0]),
        m.vertex: sp.Matrix([0, height]),
        "H": sp.Matrix([0, 0]),
    }
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def trig(match):
            sine, cosine = angular_values(points, match[2])
            value = {"sin": sine, "cos": cosine, "tg": sine / cosine}[match[1]]
            return "(" + sp.latex(sp.simplify(value)) + ")"

        text = re.sub(r"\\(sin|cos|tg)\s*\\angle\s*([ABCH]{1,3})", trig, raw)
        text = text.replace(r"\sin 60^{\circ}", r"(\frac{\sqrt{3}}{2})")

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
        values = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_all_methods_unchanged_condition_and_replay(case):
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
    assert [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ] == (
        ["Решение", "Приведем другое решение"]
        if case["group"] == "27794"
        else ["Решение"]
    )
    assert (
        plan(case, ctx).transformations == ()
        and section(ctx, "condition")["html"] == section(before, "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"][0]["asset_id"] == SOURCE
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    assert (
        profile.source_group_id == GROUPS[case["group"]]["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_unknown_statements_are_rejected(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + extra + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_fail_closed(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")


def synthetic(frame, angle):
    p, q, r = frame
    case = PARENTS["27794"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    base, height = {60: ("4", r"2\sqrt{3}"), 90: ("10", "5"), 120: (r"6\sqrt{3}", "3")}[
        angle
    ]
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {p + r}={q + r}, {p + q}={base}, высота {r}H равна {height}. Найдите угол {r}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("angle", [60, 90, 120])
def test_exact_angle_variants_both_methods_and_generated_height_geometry(frame, angle):
    case, ctx = synthetic(frame, angle)
    m = selection(ctx)[0]
    assert m.apex_angle == angle
    result = plan(case, ctx)
    assert result.answer == str(angle)
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, m)
    assert ("равного половине гипотенузы" in html) == (angle == 60)
    assert plan(case, ctx).transformations == ()
    diagram = selection(ctx)[-1]
    if diagram:
        root = ET.fromstring(diagram["svg_text"])
        lines = {
            e.get("id"): e for e in root.findall("{http://www.w3.org/2000/svg}line")
        }
        height = lines["height"]
        base = lines["base"]
        h = sp.Matrix(
            [
                float(height.get("x2")) - float(height.get("x1")),
                float(height.get("y2")) - float(height.get("y1")),
            ]
        )
        b = sp.Matrix(
            [
                float(base.get("x2")) - float(base.get("x1")),
                float(base.get("y2")) - float(base.get("y1")),
            ]
        )
        assert abs(float(h.dot(b))) < 1e-5
        assert float(height.get("x2")) == pytest.approx(
            (float(base.get("x1")) + float(base.get("x2"))) / 2
        )


@pytest.mark.parametrize("sides", list(itertools.permutations(["AB", "BC", "AC"])))
@pytest.mark.parametrize("vertex", list("ABC"))
def test_equal_side_order_and_every_requested_height_are_preserved(sides, vertex):
    case = PARENTS["27792"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {'='.join(sides)}=2\\sqrt{{3}}. Найдите высоту {vertex}H.</p>"
    )
    result = plan(case, ctx)
    assert result.answer == "3"
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "task,custom",
    [("48669", False), ("48719", False), ("48769", False), ("27794", True)],
)
def test_offline_frozen_source_reuse_and_generated_uuid_readback(task, custom):
    case = deepcopy(next(c for c in CASES if c["task"] == task))
    if custom:
        case["context"] = synthetic(("A", "B", "C"), 120)[1]
    group = case["group"]
    gateway = OfflineGateway(case)
    rule = GROUPS[group]["rule"]
    kwargs = {"parent_solution_html": parent_html(group)}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        SOURCE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"] == "applied"
    assert len(gateway.writes) == 1 and len(gateway.uploads) == int(custom)
    assert (
        _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("vertex", list("ABC"))
def test_inverse_equilateral_height_at_every_vertex(vertex):
    case = PARENTS["27793"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В равностороннем треугольнике ABC высота {vertex}H равна 8\\sqrt{{3}}. Найдите стороны этого треугольника.</p>"
    )
    result = plan(case, ctx)
    assert result.answer == "16"
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()


def test_missing_condition_change_fails_authoritative_offline_readback():
    case = deepcopy(PARENTS["27794"])
    case["context"] = synthetic(("A", "B", "C"), 120)[1]
    gateway = OfflineGateway(case, omit_condition_write=True)
    rule = GROUPS["27794"]["rule"]
    kwargs = {"parent_solution_html": parent_html("27794")}
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        SOURCE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared"
    assert _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"] == "failed"


@pytest.mark.parametrize("kind", ["extra", "url", "reference", "unknown"])
def test_unreviewed_assets_are_not_silently_replaced(kind):
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
            SOURCE, "other"
        )
    else:
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "group,text",
    [
        ("27792", r"В треугольнике ABC AB=BC=AB=2\sqrt{3}. Найдите высоту CH."),
        (
            "27794",
            r"В треугольнике ABC AC=BC, AB=4, высота AH равна 2\sqrt{3}. Найдите угол C. Ответ дайте в градусах.",
        ),
        (
            "27794",
            "В треугольнике ABC AC=BC, AB=4, высота CH равна 1. Найдите угол C. Ответ дайте в градусах.",
        ),
    ],
)
def test_inconsistent_roles_and_unsupported_exact_angles_fail_closed(group, text):
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
