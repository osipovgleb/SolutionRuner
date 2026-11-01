"""A positive whole radical factor has no separate zero-radicand root case."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_domain import (
    radical_product,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
    cases,
    operands,
    shifted_operands,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_product_proof import (
    proof,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_positive_root_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ORIGINAL = {
    "507429": (2 * S - 1, -C, sp.S.One, (), R(5, 6), (R(17, 6),)),
    "507665": (S * (2 * C - 1), -2 * C / S, sp.sqrt(2), (S,), R(5, 3), (R(5, 3),)),
    "507668": (C * (2 * S + 1), 3 * S / C, sp.sqrt(3), (C,), R(7, 6), ()),
    "511464": (C * (1 - 2 * S), S / C, sp.S.One, (C,), R(1, 6), (R(-11, 6),)),
}


def parent(e):
    p = next(c for c in CASES if c["task"] == e["group"])
    return section(p["context"]["normalized_content"], "solution")["html"]


def analysis(e, context=None):
    _, formula, interval, bounds = read(context or e["context"])
    return analyze(formula, interval, bounds, parent(e))


def plan(e, context=None):
    return get_handler(get_group_profile(e["group"]).content_rule_key).plan(
        PlanInput(context or e["context"], parent_solution_html=parent(e))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_group_coordinates_reuse_the_existing_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_complete_and_selected_roots_follow_the_original_positive_factor(e):
    a = analysis(e)
    factor, radicand, offset, poles, phase, selected = ORIGINAL[e["task"]]
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == (phase,)
    assert a.selected == selected
    assert a.radical_product.root_offset == offset
    assert a.poles == poles
    zero, remaining = cases(a, a.preferred, a.allow_inverse)
    assert zero == () and any(b.residues for b in remaining)
    for q in (phase, *selected):
        sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        assert all(sp.simplify(p.subs(sub)) != 0 for p in poles)
        assert sp.simplify(radicand.subs(sub)) >= 0
        assert sp.simplify((factor * (offset + sp.sqrt(radicand))).subs(sub)) == 0
    value = sp.lambdify((S, C), (factor, radicand), "math")
    roots = select(a.series, (-4, 4, True, True))[0]
    for k in range(-96, 97):
        q = R(k, 24)
        si, co = math.sin(float(q) * math.pi), math.cos(float(q) * math.pi)
        if (S in poles and abs(si) < 1e-10) or (C in poles and abs(co) < 1e-10):
            actual = False
        else:
            p, r = value(si, co)
            actual = r >= -1e-10 and abs(p) < 1e-10
        assert (q in roots) == actual, (e["task"], q)


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_zero_radicand_does_not_zero_the_whole_factor_in_these_sources(e):
    factor, radicand, offset, poles, _, _ = ORIGINAL[e["task"]]
    a = analysis(e)
    for q in (sp.S.Zero, sp.S.Half, sp.S.One, R(3, 2)):
        sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        if any(sp.simplify(p.subs(sub)) == 0 for p in poles):
            continue
        if sp.simplify(radicand.subs(sub)) == 0:
            assert sp.simplify((factor * (offset + sp.sqrt(radicand))).subs(sub)) != 0
            assert q not in a.residues


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_saved_answers_are_unused_and_replay_preserves_condition_and_asset(e):
    before = deepcopy(e["context"])
    p = plan(e)
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>Не использовать.</p>"
    assert plan(e, ctx) == p
    for t in p.transformations:
        assert not t["transformation_target_id"].startswith(
            ("asset:", "section:condition")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(e, ctx).transformations == ()
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert e["context"] == before
    handler = get_handler(get_group_profile(e["group"]).content_rule_key)
    assert handler.diagram_specs(before) == ()
    assert (
        BeautifulSoup(p.solution_html, "html.parser").find("img")["src"]
        == before["normalized_content"]["assets"][0]["url"]
    )


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_proof_divides_by_the_positive_whole_factor_and_keeps_parent_order(e):
    p = plan(e)
    html = p.solution_html
    assert "в том числе при нулевом радикале" in html
    assert "Рассмотрим два случая" not in html
    assert "подкоренное выражение положительно" not in html
    assert "Объединим допустимые серии обоих случаев" not in html
    assert html.index("строго положительна") < html.index(
        "Разделим на положительную скобку"
    )
    if e["task"] == "507665":
        nodes = [
            n["data-inline-latex"]
            for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
        ]
        assert nodes.index(r"(\sin x)=0") < nodes.index(r"2 (\cos x) - 1=0")
    if e["task"] != "507429":
        assert "Исходный знаменатель равен нулю" in html
        assert r"\sin2x=2\sin x\cos x" in html


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_original_svg_bytes_native_points_and_exclusions_match_the_equation(e):
    a = analysis(e)
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    validate(entry, a)
    svg = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    root = ET.fromstring(svg)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    factor, radicand, _, poles, phase, _ = ORIGINAL[e["task"]]
    cx, cy, _ = entry["circle"]
    for name in ("green_markers", "excluded_markers"):
        for point in entry[name]:
            assert point["path_d"] in paths and point["native_circle_path"] in paths
            q = R(point["angle"])
            angle = float(q) * math.pi
            radius = point["radius"]
            assert (
                math.hypot(
                    point["x"] - cx - radius * math.cos(angle),
                    point["y"] - cy + radius * math.sin(angle),
                )
                < 5
            )
            sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
            forbidden = any(sp.simplify(p.subs(sub)) == 0 for p in poles)
            if name == "green_markers":
                assert q == phase and not forbidden
                assert sp.simplify(factor.subs(sub)) == 0
            else:
                assert forbidden or sp.simplify(radicand.subs(sub)) < 0


def test_single_part_child_keeps_full_root_circle_and_has_no_interval_selection():
    e = next(c for c in CASES if c["task"] == "507668")
    a = analysis(e)
    p = plan(e)
    assert a.single_part and a.selected == () and a.selections == ()
    assert a.series == ((R(-5, 6), sp.Integer(2)),)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert (
        entry["selection_kind"] == "all_roots"
        and entry["bounds"] is None
        and entry["labels"] == []
    )
    assert "промежутку" not in p.solution_html and "отрезку" not in p.solution_html
    answer = next(
        t["value"]["html"]
        for t in p.transformations
        if "answer" in t["transformation_target_id"]
    )
    assert "а)" not in answer and "б)" not in answer


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)(1+\sqrt{\tg x})=0",
        r"(\sqrt{\tg x}+1)(\sin x)=0",
        r"(\sin x)(\sqrt{\tg x+1}+1)=0",
    ],
)
def test_zero_factor_at_zero_radicand_remains_admissible(formula):
    e = CASES[0]
    a = analyze(formula, r"[0;2\pi)", (sp.S.Zero, 2 * sp.pi, True, False), parent(e))
    assert {sp.S.Zero, sp.S.One} <= set(a.residues)
    assert a.poles == (C,)
    assert cases(a, a.preferred, a.allow_inverse)[0] == ()
    html = proof(a)[1]
    assert "уже рассмотрены в первом случае" not in html
    assert "не допускается" not in html


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)(\sqrt{\tg x}-1)=0",
        r"(\sin x)(1-\sqrt{\tg x})=0",
        r"(\sin x)(2\sqrt{\tg x}+1)=0",
        r"(\sin x)(\sqrt{\tg x}+\cos x)=0",
        r"(\sin x)(\sqrt{\tg x}+1+\frac{\sin x}{\sin x})=0",
        r"(\sin x)(\sqrt{\tg x}+\sqrt{\sin x}+1)=0",
    ],
)
def test_other_whole_factors_do_not_receive_the_positive_offset_certificate(formula):
    assert operands(formula) is None
    assert shifted_operands(formula) is None
    with pytest.raises(UnsupportedCondition):
        radical_product(formula)


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_changed_source_identity_is_rejected(e):
    ctx = deepcopy(e["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(e, ctx)


def test_zero_affine_radicand_is_kept_when_the_other_factor_also_vanishes():
    a = analyze(
        r"(\sin x+\cos x)(1+\sqrt{\tg x+1})=0",
        r"[0;2\pi)",
        (sp.S.Zero, 2 * sp.pi, True, False),
        parent(CASES[0]),
    )
    assert set(a.residues) == {R(3, 4), R(7, 4)}
    assert a.poles == (C,)
    assert r"=0\ge0" in proof(a)[1]


@pytest.mark.parametrize(
    "e", [e for e in CASES if e["task"] != "507668"], ids=lambda e: e["task"]
)
def test_interval_change_cannot_reuse_labels_from_the_original_figure(e):
    from dataclasses import replace

    a = analysis(e)
    with pytest.raises(UnsupportedCondition):
        validate(
            CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]],
            replace(a, bounds=(sp.Integer(-10), sp.Integer(10), True, True)),
        )
