"""Verify altitude-quadrilateral solutions and external rays independently."""

import itertools
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from altitude_quad_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from bs4 import BeautifulSoup
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.altitude_quad_figures import (
    ACUTE,
    OTHER,
    selection,
    source_bytes,
)


def angle(points, name):
    p, o, q = (points[n] for n in name)
    u, v = ((p[0] - o[0], p[1] - o[1]), (q[0] - o[0], q[1] - o[1]))
    cosine = sum(a * b for a, b in zip(u, v)) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1, min(1, cosine))))


def check_rows(html, m):
    alpha = float(m.alpha)
    spread = min(alpha / 4, (180 - alpha) / 8)
    values = {"A": m.alpha, "ADO": 90, "OEA": 90, "DAE": m.alpha, "DOE": 180 - m.alpha}
    for offset in [-spread, spread]:
        beta = (180 - alpha) / 2 + offset
        gamma = 180 - alpha - beta
        ar, br, cr = map(math.radians, [alpha, beta, gamma])
        length = math.sin(br) / math.sin(cr)
        cx, cy = length * math.cos(ar), length * math.sin(ar)
        points = {
            "A": (0, 0),
            "B": (1, 0),
            "C": (cx, cy),
            "D": (cx * cx / (length * length), cx * cy / (length * length)),
            "E": (cx, 0),
            "O": (cx, cx * (1 - cx) / cy),
        }
        assert beta < 90 and gamma < 90
        for name in ["ADO", "OEA", "DAE", "DOE"]:
            assert abs(angle(points, name) - float(values[name])) < 1e-8
    reverse = dict(zip(m.frame + "DEO", "ABCDEO"))
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]
        text = re.sub(
            r"\\angle\s*([ABCDEO]{3}|[ABC])",
            lambda match: (
                "(" + sp.latex(values["".join(reverse[n] for n in match[1])]) + ")"
            ),
            raw,
        ).replace(r"^{\circ}", "")
        terms = [TrigonometricParser(term).parse().value for term in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_parent_method_condition_reuse_and_empty_repeat(case):
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")["html"]
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ["answer", "solution"]:
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert (
        section(ctx, "condition")["html"] == condition
        and plan(case, ctx).transformations == ()
    )
    assert get_group_profile(case["group"]).existing_solution_policy == "rewrite"


def synthetic(kind, frame="ABC", alpha=65, extended=False, word_unit=False):
    group = "27762" if kind == "all" else "500142"
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    a, b, c = frame
    prefix = (
        "В остроугольном треугольнике ABC" if kind == "all" else "В треугольнике ABC"
    )
    acute = "" if kind == "all" else f", углы {b} и {c} — острые"
    heights = "продолжения высот" if extended else "высоты"
    unit = " градусам" if word_unit else "°"
    text = f"{prefix} угол {a} равен {alpha}{unit}{acute}, {heights} {b}D и {c}E пересекаются в точке O. Найдите угол DOE. Ответ дайте в градусах."
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    return case, ctx


@pytest.mark.parametrize("kind", ["all", "other"])
@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("word_unit", [False, True])
def test_equivalent_acute_premises_all_frames_and_degree_units(kind, frame, word_unit):
    case, ctx = synthetic(kind, frame, 43, word_unit=word_unit)
    result = plan(case, ctx)
    assert result.answer == "137"
    m = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("alpha", [120, 140])
def test_explicit_external_altitude_rays_and_generated_geometry(frame, alpha):
    case, ctx = synthetic("other", frame, alpha, True)
    result = plan(case, ctx)
    m = selection(ctx)[0]
    diagram = selection(ctx)[-1]
    root = ET.fromstring(diagram["svg_text"])
    elements = {e.get("id"): e for e in root if e.get("id")}

    def ends(name):
        item = elements[name]
        return [
            tuple(float(item.get(axis + str(i))) for axis in ["x", "y"]) for i in [1, 2]
        ]

    a, b = ends("side-AB")
    c, _ = ends("side-CA")
    _, d = ends("altitude-D")
    _, e = ends("altitude-E")
    _, o = ends("altitude-extension-D")
    _, second_o = ends("altitude-extension-E")
    points = dict(zip("ABCDEO", [a, b, c, d, e, o]))
    assert math.dist(o, second_o) < 1e-6
    assert abs(angle(points, "BAC") - alpha) < 1e-4
    assert abs(angle(points, "DOE") - (180 - alpha)) < 1e-4
    for name in ["ADO", "OEA"]:
        assert abs(angle(points, name) - 90) < 1e-4
    assert {"extension-AD", "extension-AE", "right-D", "right-E"} <= elements.keys()
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert result.answer == str(180 - alpha) and plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "kind,frame,alpha,extended,lost",
    [
        ("all", "ABC", 65, False, False),
        ("other", "ABC", 43, False, False),
        ("other", "CAB", 65, False, False),
        ("other", "ABC", 120, True, False),
        ("other", "CAB", 140, True, True),
    ],
)
def test_local_frozen_roundtrip_and_authoritative_readback(
    kind, frame, alpha, extended, lost
):
    case, ctx = synthetic(kind, frame, alpha, extended)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    source = ACUTE if kind == "all" else OTHER
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
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
    assert len(gateway.uploads) == int(frame != "ABC" or extended)
    if not lost:
        assert (
            _apply_record(gateway, record, source, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize(
    "kind,alpha,extended",
    [
        ("all", 90, False),
        ("all", 120, True),
        ("other", 90, False),
        ("other", 120, False),
        ("other", 65, True),
    ],
)
def test_degenerate_or_ambiguous_height_rays_fail_closed(kind, alpha, extended):
    case, ctx = synthetic(kind, alpha=alpha, extended=extended)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("остроугольном ", ""),
        ("BD и CE", "BD и BE"),
        ("BD и CE", "AD и CE"),
        ("угол A равен", "угол B равен"),
        ("точке O", "точке F"),
        ("угол DOE", "угол DAE"),
    ],
)
def test_missing_premises_or_inconsistent_roles_are_rejected(old, new):
    case, ctx = synthetic("all")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_method_is_rejected(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")


@pytest.mark.parametrize("kind", ["extra", "unknown", "url", "reference"])
def test_unreviewed_assets_fail_closed(kind):
    case, ctx = synthetic("all")
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


@pytest.mark.parametrize(
    "alpha", ["90{,}0000000000000000001", "179{,}999999999999999999"]
)
def test_unrepresentable_external_svg_precision_is_rejected(alpha):
    case, ctx = synthetic("other", alpha=alpha, extended=True)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [ACUTE, OTHER])
def test_audited_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))
