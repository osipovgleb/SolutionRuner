"""Validate parent angle methods with independent linear constraints and frozen replay."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from simple_angle_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
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
from solution_runner.pipelines.triangles.general.simple_angle_figures import (
    SOURCES,
    selection,
    source_bytes,
)


def check_rows(html, m):
    variables = dict(zip("ABC", sp.symbols("A B C")))
    a, b, c = (variables[m.name(v)] for v in "ABC")
    equations = [a + b + c - 180]
    equations += (
        [a - m.first, b + m.second - 180]
        if m.mode == "external"
        else [c - m.first, a - 2 * m.second]
    )
    solved = sp.solve(equations, list(variables.values()))
    values = {k: solved[v] for k, v in variables.items()}
    reverse = dict(zip(m.frame + "D", "ABCD"))

    def angle(match):
        name = match[1]
        if len(name) == 1:
            return "(" + sp.latex(values[name]) + ")"
        canonical = "".join(reverse[v] for v in name)
        canonical_values = {
            "CAD": values[m.name("A")] / 2,
            "BAD": values[m.name("A")] / 2,
            "ACD": values[m.name("C")],
            "ADB": 180 - values[m.name("A")] / 2 - values[m.name("B")],
        }
        return "(" + sp.latex(canonical_values[canonical]) + ")"

    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]
        text = re.sub(
            r"\\angle ([ABC])_\{\\mathrm\{внешн\}\}",
            lambda match: "(" + sp.latex(180 - values[match[1]]) + ")",
            raw,
        )
        text = re.sub(r"\\angle\s*([ABCD]{3}|[ABC])", angle, text).replace(
            r"^{\circ}", ""
        )
        terms = [TrigonometricParser(term).parse().value for term in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_methods_conditions_and_empty_repeat(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    condition = section(ctx, "condition")["html"]
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    untouched = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == untouched and result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], selection(ctx)[0])
    assert section(ctx, "condition")["html"] == condition
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    assert plan(case, ctx).transformations == ()


def synthetic(mode, frame, first, second):
    group = {
        "external": "27743",
        "bisector_base": "27758",
        "bisector_external": "27759",
    }[mode]
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    a, b, c = frame
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    if mode == "external":
        facts = f"угол {a} равен {first}°, внешний угол при вершине {b} равен {second}°"
        target = c
    else:
        half = (c if mode == "bisector_base" else b) + a + "D"
        facts = (
            f"{a}D — биссектриса, угол {c} равен {first}°, угол {half} равен {second}°"
        )
        target = b if mode == "bisector_base" else a + "D" + b
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {facts}. Найдите угол {target}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


@pytest.mark.parametrize("mode", ["external", "bisector_base", "bisector_external"])
@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("values", [(40, 102), (10, 31), (30, 120)])
def test_all_vertex_frames_preserve_the_same_linear_angle_method(mode, frame, values):
    first, second = (
        values
        if mode == "external"
        else {40: (50, 28), 10: (20, 50), 30: (40, 20)}[values[0]]
    )
    case, ctx = synthetic(mode, frame, first, second)
    result = plan(case, ctx)
    expected = (
        second - first
        if mode == "external"
        else 180 - 2 * second - first
        if mode == "bisector_base"
        else first + second
    )
    assert result.answer == str(expected)
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_methods_and_registered_policies_are_pinned(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой метод.</p>")
    profile = get_group_profile(group)
    handler = get_handler(profile.content_rule_key)
    assert profile.existing_solution_policy == "rewrite"
    assert handler.target.endswith("simple_angle_parent:prepare")
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize(
    "mode,frame,lost",
    [
        ("external", "ABC", False),
        ("bisector_base", "ABC", False),
        ("bisector_external", "ABC", False),
        ("external", "CAB", False),
        ("bisector_base", "BCA", False),
        ("bisector_external", "CAB", False),
        ("bisector_external", "CAB", True),
    ],
)
def test_local_frozen_uuid_roundtrip_and_authoritative_readback(mode, frame, lost):
    case, ctx = synthetic(
        mode, frame, 40 if mode == "external" else 50, 102 if mode == "external" else 28
    )
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    source = SOURCES[mode]
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, source, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize(
    "mode,first,second",
    [
        ("external", 40, 30),
        ("external", 40, 40),
        ("external", 40, 180),
        ("bisector_base", 41, 70),
        ("bisector_external", 41, 70),
    ],
)
def test_degenerate_or_negative_triangle_angles_are_rejected(mode, first, second):
    case, ctx = synthetic(mode, "ABC", first, second)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("AD — биссектриса, ", ""),
        ("AD — биссектриса", "AD — медиана"),
        ("CAD", "ACD"),
        ("угол C равен", "угол A равен"),
        ("Найдите угол B", "Найдите угол A"),
        ("AD — биссектриса", "AD — биссектриса, AD — биссектриса"),
    ],
)
def test_unknown_or_inconsistent_bisector_roles_fail_closed(old, new):
    case, ctx = synthetic("bisector_base", "ABC", 50, 28)
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("kind", ["extra", "unknown", "url", "reference"])
def test_unreviewed_assets_fail_closed(kind):
    case, ctx = synthetic("external", "ABC", 40, 102)
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


@pytest.mark.parametrize("source", list(SOURCES.values()))
def test_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


def test_exact_decimal_degrees_are_not_rounded():
    case, ctx = synthetic("bisector_base", "ABC", "50{,}25", "28{,}5")
    result = plan(case, ctx)
    assert result.answer == "72,75"
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
