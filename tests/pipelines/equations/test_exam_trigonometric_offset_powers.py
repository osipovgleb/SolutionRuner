"""Whole positive differences preserve shifted-root domains and source evidence."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    analyze_method,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    compile_equality,
    compile_quotient,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_offset_powers.json"
    ).read_text()
)["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    ctx, _ = repair_verified_condition(c["context"], validate=read)
    _, f, i, b = read(ctx)
    html = parent(c)
    if formula is not None:
        soup = BeautifulSoup(html, "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        html = str(soup)
        return analyze_method(
            formula,
            i,
            b,
            html,
            style=(S, False, False, "none", None, "inequalities"),
            preferred_scale=sp.S.One,
        )
    return analyze(formula or f, i, b, html)


def plan(c, ctx=None):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert handler.diagram_specs(ctx or c["context"]) == ()
    return handler.plan(PlanInput(ctx or c["context"], parent_solution_html=parent(c)))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equation_and_domain_independently_verify_complete_roots(c):
    a = analysis(c)
    expected = (
        ((R(1, 6),), (R(1, 6),))
        if c["task"] == "531305"
        else ((R(1, 3), R(1), R(5, 3)), (R(3), R(11, 3), R(13, 3)))
    )
    assert (a.residues, a.selected) == expected
    assert not a.strict_domain
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            t = mp.mpf(0) if abs(t) < mp.mpf("1e-55") else t
            if c["task"] == "531305":
                if t < 0 or abs(t - 1) < mp.mpf("1e-55"):
                    assert q % 2 not in a.residues
                    continue
                value = (mp.power(16, s * s) - mp.power(4, s)) / (mp.sqrt(t) - 1)
            else:
                value = mp.power(2, mp.sin(mp.pi / 2 - x)) - 2 * mp.power(
                    mp.mpf(1) / 2, 2 * t * t
                )
            assert (abs(value) < mp.mpf("1e-50")) == (q % 2 in a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_local_plan_replay_is_empty_and_source_context_unchanged(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    prepared, change = repair_verified_condition(before, validate=read)
    assert (
        p.condition_html == section(prepared["normalized_content"], "condition")["html"]
    )
    assert bool(change) == (c["task"] == "627181")
    for t in p.transformations:
        key = t["transformation_target_id"]
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((v for v in items if v["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before


@pytest.mark.parametrize(
    "numerator,offset,roots",
    [
        (r"4^{\sin x}-4", "-1", (R(1, 2),)),
        (r"4^{\sin x}-4", "+1", (R(1, 2),)),
        (r"4^{\sin x}-1", "-1", ()),
        (r"4^{\sin x}-1", "+1", (R(0),)),
        (r"4^{\sin x}-4", "", ()),
        (r"4^{\sin x}-4", r"-\frac{1}{2}", (R(1, 2),)),
        (r"4^{\sin x}-4", r"+\frac{1}{2}", (R(1, 2),)),
    ],
)
def test_zero_radicand_is_allowed_only_when_whole_denominator_is_nonzero(
    numerator, offset, roots
):
    f = r"\frac{" + numerator + r"}{\sqrt{\cos x}" + offset + "}=0"
    a = analysis(CASES[0], f)
    assert a.residues == roots
    assert a.strict_domain == (offset == "")
    html = render(a, "")
    assert html
    if not roots:
        assert "корней нет" in str(html)


def test_intermediate_figure_follows_factoring_and_precedes_formal_root_cases():
    c = CASES[0]
    a = analysis(c)
    assert a.image_position == "after-polynomial"
    html = plan(c).solution_html
    soup = BeautifulSoup(html, "html.parser")
    forms = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert r"\cosx\ge0" in forms
    assert any(r"\sqrt{\cosx}-1\ne0" == f for f in forms)
    assert not any(f == r"\cos x>0" for f in forms)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert html.count('data-asset-id="' + aid + '"') == 1
    assert (
        html.index("Вынесем общий множитель")
        < html.index(aid)
        < html.index(str(soup.find(attrs={"data-inline-latex": r"(\sin x)=0"})))
    )
    assert "исходный знаменатель" in html and "подкоренное выражение" in html


def test_missing_power_restoration_is_exact_and_positive_clearing_precedes_exponents():
    c = CASES[1]
    _, damaged, _, _ = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        compile_equality(damaged, parent(c))
    fixed, change = repair_verified_condition(c["context"], validate=read)
    assert change and fixed is not c["context"]
    condition = section(c["context"]["normalized_content"], "condition")["html"]
    assert (
        hashlib.sha256(condition.encode()).hexdigest()
        == "aa9e78dc31e357fb455f0765902e3c64492cab952d38da9fde4207a36bc3d915"
    )
    html = plan(c).solution_html
    assert html.index("Умножим уравнение на положительный множитель") < html.index(
        "равны показатели"
    )
    assert analysis(c).power_equality.cleared_power == 2 ** (2 * C * C)
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += " "
    assert repair_verified_condition(ctx, validate=read) == (ctx, None)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_svg_hash_frame_points_and_original_crosses(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    for p in (*e["green_markers"], *e["excluded_markers"]):
        assert p["path_d"] in paths
        f = p["native_frame"]
        assert f["path_d"] in paths
        q = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(q),
                p["y"] - f["cy"] + f["ry"] * math.sin(q),
            )
            < 2
        )
        for cross in p.get("cross_segments", []):
            assert any(
                n.tag.endswith(cross["tag"]) and dict(n.attrib) == cross["attributes"]
                for n in root.iter()
            )
    assert len(e["excluded_markers"]) == (3 if c["task"] == "531305" else 0)
    assert len(e["green_markers"]) == (1 if c["task"] == "531305" else 3)


@pytest.mark.parametrize(
    "denominator",
    [r"\sqrt{\cos x}-\sin x", r"\sqrt{\cos x}-1+\sin x", r"2\sqrt{\cos x}-1"],
)
def test_unreviewed_denominator_shapes_fail_closed(denominator):
    try:
        result = compile_quotient(
            r"\frac{16^{\sin^2x}-4^{\sin x}}{" + denominator + "}=0", parent(CASES[0])
        )

    except UnsupportedCondition:
        return
    assert result is None


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_both_groups_reuse_existing_runner(c):
    assert (
        get_group_profile(c["group"]).content_rule_key
        == "exam-trigonometric-polynomial-circle"
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_and_changed_interval_cannot_reuse_original_circle(c):
    from solution_runner.pipelines.equations.exam_trigonometric_circle import validate

    ctx = deepcopy(c["context"])
    asset = ctx["normalized_content"]["assets"][0]
    asset["asset_id"] = "unknown"
    asset["url"] = "/assets/unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = deepcopy(CIRCLES[aid])
    entry["bounds"][0] = "-100"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))


def test_zero_radicand_does_not_cancel_original_trigonometric_pole():
    a = analysis(
        CASES[0], r"\frac{4^{\sin x+\frac{\cos x}{\cos x}}-16}{\sqrt{\cos^2x}+1}=0"
    )
    assert C in a.poles and not a.residues
    assert "исходный знаменатель" in render(a, "")[2]


def test_rational_radicand_denominator_uses_its_positive_square():
    a = analysis(CASES[0], r"\frac{4^{\sin x}-4}{\sqrt{\frac{\cos x}{\sin x}}+1}=0")
    assert a.residues == (R(1, 2),)
    assert a.poles == (S,) and sp.expand(a.domain - C * S) == 0
    assert "положительный квадрат" in render(a, "")[2]


def test_negative_radicand_at_formal_root_is_rejected_before_offset_test():
    a = analysis(CASES[0], r"\frac{4^{\sin x+1}-1}{\sqrt{\frac{1}{\sin x}}+1}=0")
    assert a.poles == (S,) and not a.residues
    assert a.power_equality.radicand == 1 / S
    assert "подкоренное выражение" in render(a, "")[2]
