"""Independent exact geometry, proof equations and public preparation lifecycle."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_area_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
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
from solution_runner.pipelines.triangles.isosceles.area_figures import (
    ACUTE,
    OBTUSE,
    selection,
)
from solution_runner.pipelines.triangles.isosceles.area_model import read_question


def check_rows(html, m):
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]
        text = raw.replace(r"^{\circ}", "")

        def sine(match):
            value = TrigonometricParser(match[1] or match[2]).parse().value
            return "(" + sp.latex(sp.simplify(sp.sin(sp.pi * value / 180))) + ")"

        text = re.sub(r"\\sin\s*(?:(\d+)|\(([^)]+)\))", sine, text)
        values = {"S": m.area, "a": m.side, "b": m.base, "h": m.height}
        text = re.sub(
            r"(?<![A-Za-z\\])[Sabh]+(?![A-Za-z])",
            lambda match, values=values: "".join(
                "(" + sp.latex(values[c]) + ")" for c in match[0]
            ),
            text,
        )
        terms = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(v - terms[0]) == 0 for v in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_proof_rows_and_immutable_public_replay(case):
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
    # Symmetric coordinates, not the area's sine formula.
    u, v = sp.Matrix([model.base, 0]), sp.Matrix([model.base / 2, model.height])
    assert sp.simplify(abs(sp.det(sp.Matrix.hstack(u, v))) / 2 - model.area) == 0
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()
    old, new = (
        BeautifulSoup(section(c, "condition")["html"], "html.parser")
        for c in (before, ctx)
    )
    assert len(new.find_all("img")) == 1
    for soup in (old, new):
        for image in soup.find_all("img"):
            image.decompose()
    assert str(old) == str(new)
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    assert (
        profile.existing_solution_policy == "rewrite"
        and profile.source_group_id == GROUPS[case["group"]]["group_uuid"]
    )
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_statements_cannot_be_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + extra + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_fail_closed(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent=parent_html(group) + "<p>Другой способ.</p>")


@pytest.mark.parametrize("group", list(GROUPS))
def test_offline_frozen_roundtrip_and_native_asset_reuse(group):
    case = next(c for c in CASES if c["group"] == group and c["task"] != group)
    gateway = OfflineGateway(case)
    parent = PARENTS[group]["context"]
    source = parent["normalized_content"]["assets"][0]["asset_id"]
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
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "applied"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, source, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("task", ["55205", "56555"])
def test_lost_condition_write_fails_authoritative_offline_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    g = case["group"]
    gateway = OfflineGateway(case, omit_condition_write=True)
    source = PARENTS[g]["context"]["normalized_content"]["assets"][0]["asset_id"]
    rule = GROUPS[g]["rule"]
    kwargs = {"parent_solution_html": parent_html(g)}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared"
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "failed"


@pytest.mark.parametrize(
    "topology,side,base", [(1, "5", "6"), (0, "5", r"5\sqrt{2}"), (-1, "5", "8")]
)
def test_all_three_topologies_select_mathematically_compatible_picture(
    topology, side, base
):
    case = next(c for c in CASES if c["group"] == "27619")
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}Боковая сторона равнобедренного треугольника равна {side}, а основание равно {base}. Найдите площадь этого треугольника.</p>"
    )
    model, _, _, _, source, diagram = selection(ctx)
    assert model.topology == topology
    assert bool(diagram) == (topology == 0)
    if topology:
        assert source == (ACUTE if topology == 1 else OBTUSE)
    else:
        root = ET.fromstring(diagram["svg_text"])
        ns = {"s": "http://www.w3.org/2000/svg"}
        lines = {e.get("id"): e for e in root.findall("s:line", ns)}
        ends = []
        for name in ("side-left", "side-right"):
            e = lines[name]
            ends.append(
                sp.Matrix(
                    [
                        float(e.get("x1")) - float(e.get("x2")),
                        float(e.get("y1")) - float(e.get("y2")),
                    ]
                )
            )
        assert abs(float(ends[0].dot(ends[1]))) < 1e-5
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
def test_named_equal_side_orientations_preserve_vertices_and_replay(frame):
    p, q, r = frame
    case = CASES[0]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}В равнобедренном треугольнике ABC угол {r} равен 30°. Боковые стороны {p + r}={q + r}=14. Найдите площадь этого треугольника.</p>"
    )
    m = selection(ctx)[0]
    assert m.apex == r
    result = plan(case, ctx)
    assert result.answer == "49"
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "given",
    [
        "Боковая сторона равнобедренного треугольника равна 5, а основание равно 10",
        "Боковая сторона равнобедренного треугольника равна 5, а основание равно 11",
        "Боковая сторона равнобедренного треугольника равна 0, а основание равно 1",
    ],
)
def test_degenerate_or_impossible_triangles_fail_closed(given):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + given + ". Найдите площадь этого треугольника.</p>", "")


@pytest.mark.parametrize("kind", ["right", "apex_b"])
def test_generated_picture_offline_uuid_roundtrip(kind):
    original = next(
        c for c in CASES if c["task"] == ("27619" if kind == "right" else "27589")
    )
    case = deepcopy(original)
    condition = section(case["context"], "condition")
    image = BeautifulSoup(condition["html"], "html.parser").img
    text = (
        r"Боковая сторона равнобедренного треугольника равна 5, а основание равно 5\sqrt{2}. Найдите площадь этого треугольника."
        if kind == "right"
        else "В равнобедренном треугольнике ABC угол B равен 30°. Боковые стороны AB=CB=14. Найдите площадь этого треугольника."
    )
    condition["html"] = f"<p>{image}{text}</p>"
    gateway = OfflineGateway(case)
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        ACUTE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert _apply_record(gateway, record, ACUTE, rule, **kwargs)["status"] == "applied"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, ACUTE, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("kind", ["extra", "url", "reference", "unknown"])
def test_unreviewed_asset_metadata_is_rejected(kind):
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
