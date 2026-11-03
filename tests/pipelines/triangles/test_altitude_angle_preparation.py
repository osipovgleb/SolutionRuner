"""Check the altitude-angle extension through the existing public angle handler."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from altitude_angle_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from bs4 import BeautifulSoup
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
from solution_runner.pipelines.triangles.isosceles.angle_figures import (
    ALTITUDE,
    selection,
    source_bytes,
)


def check_rows(html, model):
    symbols = dict(zip("ABC", sp.symbols("A B C")))
    p, q = model.base_vertices
    solved = sp.solve(
        [
            symbols[p] - symbols[q],
            sum(symbols.values()) - 180,
            symbols[model.other_base_vertex] + model.given_value - 90,
        ],
        list(symbols.values()),
    )
    values = {name: solved[value] for name, value in symbols.items()}
    assert values[model.apex] == model.answer
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def angle(match):
            name = match[1]
            value = values[name] if len(name) == 1 else model.given_value
            assert len(name) == 1 or name == model.given_vertex
            return "(" + sp.latex(value) + ")"

        text = re.sub(r"\\angle\s*([ABCD]{3}|[ABC])", angle, raw).replace(
            r"^{\circ}", ""
        )
        terms = [TrigonometricParser(term).parse().value for term in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_methods_condition_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    original_condition = section(ctx, "condition")["html"]
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    assert get_handler(GROUPS["27760"]["rule"]).diagram_specs(ctx) == ()
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, selection(ctx)[0])
    assert (
        BeautifulSoup(html, "html.parser").section["data-solution-title"] == "Решение"
    )
    assert section(ctx, "condition")["html"] == original_condition
    assert plan(case, ctx).transformations == ()


def synthetic(frame, value, reverse=False):
    p, q, c = frame
    case = PARENTS["27760"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    named = "D" + p + q if reverse else q + p + "D"
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {p}{c}={q}{c}, {p}D — высота, "
        f"угол {named} равен {value}°. Найдите угол {c}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("value", [15, 24, 45, 60, 75])
@pytest.mark.parametrize("reverse", [False, True])
def test_all_vertex_frames_and_foot_topologies(frame, value, reverse):
    case, ctx = synthetic(frame, value, reverse)
    result = plan(case, ctx)
    assert result.answer == str(2 * value)
    replay(ctx, result.transformations)
    model = selection(ctx)[0]
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("value", [24, 45, 60])
def test_generated_diagram_encodes_equal_sides_and_perpendicular_height(value):
    _, ctx = synthetic("CAB", value)
    root = ET.fromstring(selection(ctx)[-1]["svg_text"])
    elements = {e.get("id"): e for e in root if e.get("id")}

    def ends(name):
        line = elements[name]
        return [
            sp.Matrix(
                [sp.Float(line.get("x" + str(i))), sp.Float(line.get("y" + str(i)))]
            )
            for i in (1, 2)
        ]

    p, q = ends("base")
    _, c = ends("side-left")
    start, d = ends("altitude")
    assert (start - p).norm() < 1e-5
    assert abs(float((c - p).norm() - (c - q).norm())) < 1e-5
    assert abs(float((d - p).dot(c - q))) < 1e-4
    assert abs(float(sp.det(sp.Matrix.hstack(d - q, c - q)))) < 1e-4
    projection = float((d - q).dot(c - q) / (c - q).dot(c - q))
    if value < 45:
        assert 0 < projection < 1 and "side-extension" not in elements
    elif value == 45:
        assert (d - c).norm() < 1e-5 and "coincident-equal-0" in elements
    else:
        assert projection > 1 and "side-extension" in elements
    assert {"label-A", "label-B", "label-C", "label-D", "right-D"} <= elements.keys()


@pytest.mark.parametrize(
    "change",
    [
        ("AD — высота, ", ""),
        ("AD — высота", "CD — высота"),
        ("BAD", "CAD"),
        ("BAD", "ABD"),
        ("BAD", "B"),
        ("24°", "90°"),
        ("24°", "0°"),
        ("24°", "120°"),
        ("Найдите угол C", "Найдите угол A"),
        ("AD — высота", "AD — биссектриса"),
        ("AC=BC", "AC=AC"),
        ("AC=BC", "AC=AB"),
        ("AD — высота", "AD — высота, AD — высота"),
    ],
)
def test_missing_or_contradictory_facts_fail_closed(change):
    case, ctx = synthetic("ABC", 24)
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        *change
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_unreviewed_statements_fail_closed(extra):
    case, ctx = synthetic("ABC", 24)
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_changed_parent_is_not_ignored():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=parent_html("27760") + "<p>Другой метод.</p>")


@pytest.mark.parametrize("kind", ["extra", "reference", "url", "unknown"])
def test_unreviewed_assets_fail_closed(kind):
    case, ctx = synthetic("ABC", 24)
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif kind == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            ALTITUDE, "other"
        )
    elif kind == "url":
        asset["url"] = "/assets/other"
    else:
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "value,lost", [(24, False), (45, False), (60, False), (60, True)]
)
def test_local_frozen_roundtrip_and_authoritative_readback(value, lost):
    case, ctx = synthetic("ABC", value)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS["27760"]["rule"]
    kwargs = {"parent_solution_html": parent_html("27760")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        ALTITUDE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, ALTITUDE, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(value != 24)
    if not lost:
        assert (
            _apply_record(gateway, record, ALTITUDE, rule, **kwargs)["status"]
            == "already_complete"
        )


def test_binding_uses_existing_angle_handler_and_pinned_source():
    profile = get_group_profile("27760")
    handler = get_handler(profile.content_rule_key)
    assert profile.existing_solution_policy == "rewrite"
    assert handler.target.endswith("angle_parent:prepare")
    assert handler.requires_frozen_manifest and handler.verify_content_readback
    assert source_bytes(ALTITUDE).lstrip().startswith((b"<?xml", b"<svg"))
