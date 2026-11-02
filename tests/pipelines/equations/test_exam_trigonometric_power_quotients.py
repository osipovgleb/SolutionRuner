"""Equal positive powers retain every original radical and trigonometric pole."""

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
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    compile_quotient,
    review_quotient_parent,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_power_quotients.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, formula=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent(c))


def plan(c, context=None):
    ctx = context or c["context"]
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_condition_and_original_sources(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((v for v in items if v["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert all(
        a in ctx["normalized_content"]["assets"]
        for a in before["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) == len(
        before["normalized_content"]["assets"]
    ) + (c["task"] == "673368")
    assert c["context"] == before


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_are_checked_from_original_powers_and_strict_domain(
    c,
):
    a = analysis(c)
    expected = DATA["expected"][c["task"]]
    assert a.residues == tuple(map(R, expected["full"]))
    assert a.selected == tuple(map(R, expected["selected"]))
    with mp.workdps(65):
        for n in range(-216, 217):
            q = R(n, 48)
            x = mp.mpf(n) * mp.pi / 48
            sine, cosine = mp.sin(x), mp.cos(x)
            sine = mp.mpf(0) if abs(sine) < mp.mpf("1e-55") else sine
            cosine = mp.mpf(0) if abs(cosine) < mp.mpf("1e-55") else cosine
            if c["task"] in ("516274", "516255"):
                base, number, weight = (
                    (3, 2, 11) if c["task"] == "516274" else (2, 3, 7)
                )
                numerator = mp.power(base**2, mp.sin(2 * x)) - mp.power(
                    base, 2 * mp.sqrt(number) * sine
                )
                radicand = weight * sine
            elif c["task"] in ("673368", "624488"):
                base, weight = (25, 5) if c["task"] == "673368" else (2022, -2021)
                numerator = mp.power(base, mp.cos(2 * x)) - mp.power(base, cosine)
                radicand = weight * sine
            else:
                numerator = mp.power(2, mp.sin(2 * x)) - mp.power(
                    2, mp.sqrt(3) * cosine
                )
                radicand = sine / cosine - 1 if cosine else -1
            expected_root = radicand > 0 and abs(numerator) < mp.mpf("1e-50")
            assert expected_root == (q % 2 in a.residues)
    assert a.strict_domain
    assert a.power_equality.radicand is not None


@pytest.mark.parametrize(
    "c",
    [c for c in CASES if c["context"]["normalized_content"]["assets"]],
    ids=lambda c: c["task"],
)
def test_original_svg_bytes_green_points_and_native_crosses_are_preserved(c):
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
    assert len(e["green_markers"]) == 1
    if c["task"] in ("516274", "516255"):
        assert (
            len(e["excluded_markers"]) == 1
            and len(e["excluded_markers"][0]["cross_segments"]) == 2
        )
    validate(e, analysis(c))
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


def test_assetless_child_uses_the_parent_circle_style_with_its_own_root_and_cross():
    c = case("673368")
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    (spec,) = h.diagram_specs(c["context"])
    root = ET.fromstring(spec["svg_text"])
    frame = CIRCLES[
        case("516274")["context"]["normalized_content"]["assets"][0]["asset_id"]
    ]["circle"]
    cx, cy, radius = frame[0], frame[1] + 25, frame[2]
    for role, q in [("selected-root", R(2, 3)), ("excluded-root", R(4, 3))]:
        p = next(n for n in root.iter() if n.get("data-role") == role)
        assert R(p.get("data-angle")) == q
        assert (
            math.hypot(
                float(p.get("cx")) - cx - radius * math.cos(float(q) * math.pi),
                float(p.get("cy")) - cy + radius * math.sin(float(q) * math.pi),
            )
            < 1e-6
        )
    arc = next(n for n in root.iter() if n.get("data-role") == "interval-arc")
    assert arc.get("data-bounds") == "-11/2;-9/2" and " 0 0 0 " in arc.get("d")
    crosses = [n for n in root.iter() if n.get("data-role") == "excluded-cross"]
    assert len(crosses) == 2
    assert any(
        n.get("data-role") == "projection" and n.get("stroke-dasharray") == "5,5"
        for n in root.iter()
    )
    label = next(n for n in root.iter() if n.get("data-role") == "selected-label")
    assert [n.text for n in label.iter() if n.tag.endswith("text")] == ["−16π", "3"]
    assert (
        BeautifulSoup(plan(c).solution_html, "html.parser")
        .find("img")["src"]
        .startswith("/assets/preview-")
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_domain_precedes_powers_and_every_rejected_series_has_an_original_reason(c):
    p = plan(c)
    html = p.solution_html
    assert html.index("ненулевым") < html.index("положительному основанию")
    assert "подкоренное выражение" in html or "исходный знаменатель" in html
    assert html.count("Оставим только серии") == 1
    if c["task"] == "698236":
        a = analysis(c)
        assert a.poles == (C,)
        assert a.domain == C * (S - C) or sp.expand(a.domain - C * (S - C)) == 0
        assert r"\text{исходный знаменатель}=0" in html
    if c["task"] == "624488":
        assert analysis(c).series == ((-R(2, 3), 2),)


def test_fresh_common_bases_and_opposite_sine_domain_reuse_the_same_rule():
    c = case("516274")
    formula = r"\frac{(\frac{1}{9})^{\sin 2x}-(\frac{1}{3})^{2\sqrt{2}\sin x}}{\sqrt{11\sin x}}=0"
    a = analysis(c, formula)
    assert a.residues == (R(1, 4),)
    assert a.power_equality.cleared_power != 1
    assert "на положительный множитель" in render(a, "")[2]
    formula = r"\frac{9^{\sin 2x}-3^{2\sqrt{2}\sin x}}{\sqrt{-11\sin x}}=0"
    a = analysis(c, formula)
    assert a.residues == (R(7, 4),) and a.series == ((-R(1, 4), 2),)


def test_original_cancelled_exponent_denominator_is_not_lost():
    c = case("516274")
    formula = r"\frac{9^{\sin 2x+\frac{\cos x}{\cos x}}-3^{2\sqrt{2}\sin x+2}}{\sqrt{11\sin x}}=0"
    a = analysis(c, formula)
    assert a.poles == (C,) and a.residues == (R(1, 4),)
    formula = r"\frac{4^{\sin x+\frac{\cos x}{\cos x}}-16}{\sqrt{\sin x}}=0"
    a = analysis(c, formula)
    assert a.poles == (C,) and a.residues == ()
    assert r"\text{исходный знаменатель}=0" in render(a, "")[2]


def test_constant_denominator_weight_keeps_the_tangent_pole_and_strict_domain():
    c = case("698236")
    formula = r"\frac{2^{\sin 2x}-2^{\sqrt{3}\cos x}}{\sqrt{\frac{\tg x-1}{2}}}=0"
    a = analysis(c, formula)
    assert a.poles == (C,) and a.residues == (R(1, 3),)
    assert sp.cancel(a.power_equality.radicand - (S - C) / (2 * C)) == 0
    assert "положительный квадрат знаменателя" in render(a, "")[2]


def test_common_positive_power_product_is_cancelled_with_an_explicit_reason():
    c = case("516274")
    formula = r"\frac{5^{\cos x}\cdot9^{\sin 2x}-5^{\cos x}\cdot3^{2\sqrt{2}\sin x}}{\sqrt{11\sin x}}=0"
    a = analysis(c, formula)
    assert a.residues == (R(1, 4),)
    html = render(a, "")[2]
    assert "общий положительный множитель" in html


@pytest.mark.parametrize(
    "parent_html",
    [
        r'<p><span data-inline-latex="\sin x=\frac{\sqrt{3}}{2}"></span></p>',
        r'<p><span data-inline-latex="2\sin2x-2\sqrt{2}\cos x=0"></span></p>',
        "<p>Другое решение</p>" + parent(case("698236")),
        "<p>Еще одно решение</p>" + parent(case("698236")),
        parent(case("698236")) + r'<p><span data-inline-latex="t=\sin x"></span></p>',
    ],
)
def test_parent_roots_alone_wrong_exponent_or_unreviewed_method_do_not_certify_powers(
    parent_html,
):
    _, formula, _, _ = read(case("698236")["context"])
    with pytest.raises(UnsupportedCondition):
        compile_quotient(formula, parent_html, preferred=C)


def test_complete_parent_exponent_step_is_checked_without_using_the_answer():
    expected = 2 * S * C - sp.sqrt(3) * C
    review_quotient_parent(parent(case("698236")), expected)
    with pytest.raises(UnsupportedCondition):
        review_quotient_parent(parent(case("698236")), 2 * S * C - sp.sqrt(2) * C)


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{2^{\sin x}-3^{\cos x}}{\sqrt{\sin x}}=0",
        r"\frac{(-2)^{\sin x}-2^{\cos x}}{\sqrt{\sin x}}=0",
        r"\frac{9^{\sin2x}-3^{2\sin x}+1}{\sqrt{\sin x}}=0",
        r"\frac{2^{\sin x}-2^{\sin x}}{\sqrt{\sin x}}=0",
        r"\frac{9^{\sin2x}-3^{2\sin x}}{\sqrt{\frac{\sin x}{1+\cos x}}}=0",
        r"\frac{9^{\sin2x}-3^{2\sin x}}{\sqrt{\sin x}-1}=0",
    ],
)
def test_unreviewed_powers_extra_terms_identity_and_denominator_shapes_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analysis(case("516274"), formula)


@pytest.mark.parametrize(
    "c",
    [c for c in CASES if c["context"]["normalized_content"]["assets"]],
    ids=lambda c: c["task"],
)
def test_unknown_source_or_changed_interval_cannot_reuse_the_circle(c):
    ctx = deepcopy(c["context"])
    a = ctx["normalized_content"]["assets"][0]
    a["asset_id"] = "unknown"
    a["url"] = "/assets/unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    entry = deepcopy(
        CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    entry["bounds"][0] = "-100"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))


@pytest.mark.parametrize("key", DATA["groups"])
def test_exact_catalog_registration_uses_the_existing_shared_handler(key):
    p = get_group_profile(key)
    g = DATA["groups"][key]
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert p.group_order_index == g["order_index"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
