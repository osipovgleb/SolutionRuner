"""Exact tangent series, radical domains and locally repaired circle geometry."""

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
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    compile_equation,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_domain import (
    radical_product,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_domain.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
A2, A3 = sp.atan(2) / sp.pi, sp.atan(3) / sp.pi
RESIDUES = {
    "514472": (sp.Rational(5, 4), sp.Rational(7, 4)),
    "514473": (sp.Rational(3, 4), sp.Rational(5, 4)),
    "515686": (1 - A3, 1 - A2, 2 - A3, 2 - A2),
    "500815": (0, sp.Rational(1, 6), sp.Rational(5, 6), 1),
    "514025": (
        sp.Rational(1, 2),
        sp.Rational(3, 4),
        sp.Rational(5, 4),
        sp.Rational(3, 2),
    ),
    "514044": (sp.Rational(1, 2), sp.Rational(5, 4), sp.Rational(3, 2)),
}
SELECTED = {
    "514472": (sp.Rational(7, 4),),
    "514473": (sp.Rational(5, 4),),
    "515686": (-1 - A3, -1 - A2),
    "500815": (-2, -sp.Rational(11, 6), -sp.Rational(7, 6)),
    "514025": (-sp.Rational(5, 2), -sp.Rational(3, 2), -sp.Rational(5, 4)),
    "514044": (-sp.Rational(19, 4), -sp.Rational(9, 2), -sp.Rational(7, 2)),
}
ORIGINAL = {
    "514472": 2 * sp.cos(X) ** 2 + 1 - 2 * sp.sqrt(2) * sp.cos(3 * sp.pi / 2 - X),
    "514473": 2 * sp.sin(X) ** 2 - 3 * sp.sqrt(2) * sp.sin(sp.pi / 2 - X) - 4,
    "515686": sp.tan(X) ** 2 + 5 * sp.tan(X) + 6,
    "500815": sp.cos(2 * X) - 1 + sp.cos(sp.pi / 2 - X),
    "514025": sp.sqrt(2) * sp.sin(sp.pi / 2 + X) ** 2 + sp.cos(X),
    "514044": (sp.sqrt(2) * sp.sin(X) + 1) * sp.sqrt(-5 * sp.cos(X)),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, interval, bounds = read(c["context"])
    return analyze(f, interval, bounds, parent(c))


def prepared(c):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    specs = handler.diagram_specs(c["context"])
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in specs
    )


def plan(c, context=None, generated=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c),
            generated_solution_assets=prepared(c) if generated is None else generated,
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_preserves_catalog_and_reuses_the_same_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.group_order_index,
        p.theme_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], g["order"], 4, "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_roots_and_independently_written_original_equations(c):
    a = analysis(c)
    assert a.residues == RESIDUES[c["task"]] and a.selected == SELECTED[c["task"]]
    for q in (*a.residues, *a.selected):
        x = sp.expand(q * sp.pi)
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, x)) == 0
        if c["task"] == "515686":
            assert sp.simplify(sp.cos(x)) != 0
        if c["task"] == "514044":
            assert sp.simplify(-5 * sp.cos(x)) >= 0
    if c["task"] != "515686":
        grid = tuple(
            sp.Rational(i, 12)
            for i in range(24)
            if sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi * i / 12)) == 0
            and (c["task"] != "514044" or sp.cos(sp.pi * i / 12) <= 0)
        )
        assert grid == a.residues


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_answers_are_unused_and_replay_preserves_sources_and_conditions(c):
    ctx = deepcopy(c["context"])
    before = deepcopy(ctx)
    p = plan(c, ctx)
    assert ctx == before
    assert p.condition_html == next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>UNUSED9999</p>"
    assert plan(c, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        if key.startswith("asset:"):
            ctx["normalized_content"]["assets"].append(t["value"])
        else:
            assert key.startswith(("section:answer", "section:solution"))
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["transformation_target_id"] == key
            ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    for a in before["normalized_content"]["assets"]:
        assert a in ctx["normalized_content"]["assets"]
    assert "Примечание" not in p.solution_html
    if c["task"] in ("514473", "514044"):
        assert len(prepared(c)) == 1
        with pytest.raises(UnsupportedCondition):
            plan(c, generated=())
    else:
        assert prepared(c) == ()
        image = BeautifulSoup(p.solution_html, "html.parser").find("img")
        assert (
            image["data-asset-id"] == ctx["normalized_content"]["assets"][0]["asset_id"]
        )


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (A2, A3, -1),
        (A2, -A3, 1),
        (-1 - A3, -1 - A2, -1),
        (A2, sp.Rational(1, 4), 1),
        (A2, sp.Rational(1, 2), -1),
        (-A2, -sp.Rational(1, 2), 1),
        (1 - A3, 2 - A2, -1),
    ],
)
def test_arctangents_are_compared_exactly(a, b, expected):
    assert compare_q(a, b) == expected and compare_q(b, a) == -expected


def test_tangent_open_poles_and_principal_period_are_retained():
    a = analysis(case("515686"))
    assert {p for _, p in a.series} == {1}
    html = plan(case("515686")).solution_html
    assert r"\cos x\ne0" in html and r"\arctan" in html
    assert "не входит в отрезок" not in html
    assert select(a.series, (sp.Rational(-1, 2), sp.Rational(1, 2), True, True))[0] == (
        -A3,
        -A2,
    )
    assert (
        compare_q(decode({"rational": "-1", "atan": "3", "coefficient": -1}), -1 - A3)
        == 0
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\tg 2x=0",
        r"\tg(x+\frac{\pi}{2})=1",
        r"\frac{\tg x}{\tg x}=1",
        r"\tg x+\sin x=0",
        r"\tg^3 x=1",
    ],
)
def test_unreviewed_tangent_equations_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equation(formula)


def test_radical_product_retains_zero_radicand_and_excludes_the_other_sine_branch():
    a = analysis(case("514044"))
    assert sp.Rational(7, 4) not in a.residues
    assert sp.Rational(1, 2) in a.residues and sp.Rational(3, 2) in a.residues
    html = plan(case("514044")).solution_html
    assert "нулевым подкоренным" in html and "не входит в область" in html
    assert r"(\cos x)\le0" in html
    assert r"\frac{7 \pi}{4}" in html


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x+1)\sqrt{1-5\cos x}=0",
        r"\sqrt{-5\cos x}+1=0",
        r"(\sin x+1)\sqrt{-5\cos x}=1",
        r"(\tg x+1)\sqrt{-5\cos x}=0",
    ],
)
def test_other_radical_grammars_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        radical_product(formula)


def test_parent_circle_letters_describe_only_the_matching_source_points():
    html = plan(case("500815")).solution_html
    assert "точками A и B" in html and "точками C и D" in html
    assert "точками A" not in plan(case("514025")).solution_html
    assert analysis(case("500815")).bounds[-1] is False


def test_prepared_circle_replaces_only_the_wrong_number_line():
    c = case("514473")
    svg = prepared(c)[0]["svg_text"]
    root = ET.fromstring(svg)
    nodes = [e for e in root.iter() if e.get("data-root-phases")]
    assert len(nodes) == 1 and nodes[0].get("data-root-phases") == "3/4 5/4"
    for q, node in zip((sp.Rational(3, 4), sp.Rational(5, 4)), nodes[0]):
        assert (
            math.hypot(
                float(node.get("cx")) - (125 + 82 * math.cos(float(q) * math.pi)),
                float(node.get("cy")) - (125 - 82 * math.sin(float(q) * math.pi)),
            )
            < 1e-5
        )
    assert 'd="M43 125A82 82 0 1 0 125 43"' in svg
    assert 'data-angle="5/2"' in svg and 'data-angle="5/4"' in svg
    assert any(e.get("source_kind") == "number-line" for e in CIRCLES.values())


def test_corrected_radical_circle_moves_both_marker_layers_and_preserves_labels():
    import gzip
    import re

    identifier, entry = next(
        (i, e) for i, e in CIRCLES.items() if e["task"] == "514044"
    )
    original = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    fixed = ET.fromstring((DIRECTORY / entry["corrected_file"]).read_text())
    old_nodes, new_nodes = list(original.iter()), list(fixed.iter())
    assert len(old_nodes) == len(new_nodes)
    lower = {
        "".join(p["path_d"].split()): p
        for p in entry["green_markers"]
        if p.get("inaccurate")
    }
    cx, cy, _ = entry["circle"]
    shifted = []
    for old, new in zip(old_nodes, new_nodes):
        assert old.tag == new.tag and old.get("d") == new.get("d")
        point = lower.get("".join(old.get("d", "").split()))
        if point:
            dx, dy = map(
                float,
                re.fullmatch(
                    r"translate\(([-\d.]+) ([-\d.]+)\)", new.get("transform")
                ).groups(),
            )
            q = float(decode(point["angle"])) * math.pi
            assert (
                math.hypot(
                    point["x"] + dx - cx - 62.4 * math.cos(q),
                    point["y"] + dy - cy + 62.4 * math.sin(q),
                )
                < 1e-7
            )
            shifted.append(point["angle"])
        elif old.get("stroke") == "#FF0000":
            assert new.get("transform")
            assert {
                k: v for k, v in new.attrib.items() if k != "transform"
            } == old.attrib
        elif old.get("stroke-dasharray"):
            assert new.get("y1") == new.get("y2")
            assert abs(float(new.get("y1")) - (cy + 62.4 / math.sqrt(2))) < 1e-7
        else:
            assert old.attrib == new.attrib
    assert shifted.count("5/4") == shifted.count("7/4") == 2


def test_unknown_inverse_angle_combinations_and_label_schema_fail_closed():
    with pytest.raises(UnsupportedCondition):
        compare_q(A2 - A3, sp.Rational(1, 10))
    with pytest.raises(UnsupportedCondition):
        decode({"rational": "0", "atan": "2", "coefficient": 0})
