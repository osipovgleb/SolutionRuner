"""Independent half-angle geometry checks both parent methods and public replay."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_cosine_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
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
from solution_runner.pipelines.triangles.isosceles.cosine_figures import (
    SOURCE,
    selection,
)


def check_rows(html, m):
    value = TrigonometricParser(m.length_raw).parse().value
    theta = sp.pi * m.apex_angle / 360
    side = value if m.given_kind == "side" else sp.simplify(value / (2 * sp.sin(theta)))
    base = sp.simplify(2 * side * sp.sin(theta))
    p, q = m.base_vertices
    points = {
        p: sp.Matrix([-base / 2, 0]),
        q: sp.Matrix([base / 2, 0]),
        m.apex: sp.Matrix([0, sp.simplify(side * sp.cos(theta))]),
    }
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def function(match):
            sine, cosine = angular_values(points, match[2])
            return "(" + sp.latex(sine if match[1] == "sin" else cosine) + ")"

        text = re.sub(r"\\(sin|cos)\s*\\angle\s*([ABC]{1,3})", function, raw)

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

        text = re.sub(r"\\angle\s*([ABC])", angle, text).replace(r"^{\circ}", "")

        def length(match):
            a, b = points[match[0][0]], points[match[0][1]]
            return "(" + sp.latex(sp.simplify((a - b).norm())) + ")"

        text = re.sub(r"[ABC]{2}", length, text)
        terms = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(v - terms[0]) == 0 for v in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_all_methods_and_immutable_empty_replay(case):
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
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, model)
    titles = [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ]
    assert titles == (
        ["Решение", "Приведем другое решение"]
        if case["group"] == "27799"
        else ["Решение"]
    )
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "condition")["html"] == section(before, "condition")["html"]
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
def test_extra_statements_are_rejected(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + extra + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_fail_closed(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("angle", [60, 90, 120])
@pytest.mark.parametrize("kind", ["base", "side"])
def test_both_directions_frames_and_topologies_preserve_geometry_and_replay(
    frame, angle, kind
):
    p, q, r = frame
    group = "27799" if kind == "base" else "27800"
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    raw = (r"10\sqrt{2}" if kind == "base" else r"5\sqrt{2}") if angle == 90 else "10"
    expected = "10" if angle in {60, 90} else None
    if angle == 120:
        raw = r"2\sqrt{3}"
        expected = "2" if kind == "base" else "6"
    given = (p + q if kind == "base" else p + r) + "=" + raw
    target = p + r if kind == "base" else p + q
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {p + r}={q + r}, угол {r} равен {angle}°, {given}. Найдите {target}.</p>"
    )
    m = selection(ctx)[0]
    assert m.apex == r
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "task,custom", [("49019", False), ("49049", False), ("27799", True)]
)
def test_offline_frozen_readback_and_generated_uuid(task, custom):
    case = deepcopy(next(c for c in CASES if c["task"] == task))
    group = case["group"]
    if custom:
        condition = section(case["context"], "condition")
        image = BeautifulSoup(condition["html"], "html.parser").img
        condition["html"] = (
            f"<p>{image}В треугольнике ABC AC=BC, угол C равен 90°, AB=10\\sqrt{{2}}. Найдите AC.</p>"
        )
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


@pytest.mark.parametrize("kind", ["extra", "url", "reference", "unknown"])
def test_unreviewed_assets_cannot_be_replaced_silently(kind):
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


@pytest.mark.parametrize("value", [0, 180, 181])
def test_degenerate_included_angles_are_rejected(value):
    ctx = deepcopy(CASES[0]["context"])
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "120", str(value)
    )
    with pytest.raises(ContentPlanError):
        plan(CASES[0], ctx)
