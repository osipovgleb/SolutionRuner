"""Original domains, cancellation, radicals, exact inverse roots and one-part tasks."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_original_domains.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
ALPHA = sp.Rational(1, 2) - sp.acos(sp.Rational(5, 13)) / sp.pi
BETA = sp.Rational(1, 2) - sp.acos(sp.Rational(3, 5)) / sp.pi
SELECTED = {
    "507644": "11/3 4",
    "511458": "",
    "509820": "-7/6",
    "511598": "-1/6 1/6 5/6",
    "514240": "13/4",
    "504240": "2 17/6 3",
    "510354": "2 17/6 3",
    "510362": "2 7/3 3",
    "510372": "-1 -5/6 0",
    "525023": (-3, -2, ALPHA - 2),
    "525046": "-3 -2",
    "505498": "-11/6 -3/2 -7/6",
    "517199": "-13/6 -3/2",
    "517237": "-11/6 -3/2 -7/6",
    "501395": "-4/3 -2/3",
    "511355": "1/6",
    "501415": "-13/6 -5/6",
    "513683": "-8/3",
}
RESIDUES = {
    "507644": "0 5/3",
    "511458": "1/6 1/4 5/6",
    "509820": "5/6 7/6",
    "511598": "1/6 5/6 7/6 11/6",
    "514240": "5/4 7/4",
    "504240": "0 5/6 1",
    "510354": "0 5/6 1",
    "510362": "0 1/3 1",
    "510372": "0 1 7/6",
    "525023": (0, ALPHA, 1),
    "525046": (0, BETA, 1),
    "505498": "1/6 1/2 5/6",
    "517199": "1/2 7/6 11/6",
    "517237": "1/6 1/2 5/6",
    "501395": "2/3 4/3",
    "511355": "1/6 5/6",
    "501415": "7/6 11/6",
    "513683": "2/3 4/3",
}
ORIGINAL = {
    "507644": (c - 1) * (sp.tan(X) + sp.sqrt(3)) * sp.sqrt(c),
    "511458": (2 * s - 1) * (sp.cot(X) - 1) * sp.sqrt(s),
    "509820": sp.sin(2 * X) / sp.cos(sp.pi / 2 + X) - sp.sqrt(3),
    "511598": sp.sin(4 * X) / sp.cos(3 * sp.pi / 2 + 2 * X) - 1,
    "514240": sp.sin(2 * X) / sp.sin(7 * sp.pi / 2 - X) - sp.sqrt(2),
    "504240": (2 * s * s - s) / (2 * c - sp.sqrt(3)),
    "510362": (2 * s * s - sp.sqrt(3) * s) / (2 * c + 1),
    "510372": (2 * s * s + s) / (2 * c - sp.sqrt(3)),
    "525023": (13 * s * s - 5 * s) / (13 * c + 12),
    "525046": (5 * s * s - 3 * s) / (5 * c + 4),
    "505498": 1 / s**2 - 3 / s + 2,
    "517199": 1 / s**2 + 1 / sp.cos(7 * sp.pi / 2 + X) - 2,
    "517237": 1 / s**2 - 3 / sp.cos(11 * sp.pi / 2 + X) + 2,
    "501395": s * (2 * s - 3 * sp.cot(X)) - 3,
    "511355": c * (2 * c + 7 * sp.tan(X)) - 5,
    "501415": c * (2 * c + sp.tan(X)) - 1,
}
ORIGINAL["510354"] = ORIGINAL["504240"]
ORIGINAL["513683"] = ORIGINAL["501395"]
POLES = {
    "509820": s,
    "511598": sp.sin(2 * X),
    "514240": c,
    "504240": 2 * c - sp.sqrt(3),
    "510354": 2 * c - sp.sqrt(3),
    "510362": 2 * c + 1,
    "510372": 2 * c - sp.sqrt(3),
    "525023": 13 * c + 12,
    "525046": 5 * c + 4,
    "505498": s,
    "517199": s,
    "517237": s,
    "501395": s,
    "511355": c,
    "501415": c,
    "513683": s,
}


def expected(value):
    return (
        tuple(map(sp.Rational, value.split()))
        if isinstance(value, str)
        else tuple(map(sp.sympify, value))
    )


def allowed(task, q):
    angle = q * sp.pi
    if task in ("507644", "511458"):
        return (
            sp.cos(angle) if task == "507644" else sp.sin(angle)
        ).is_positive is True
    return sp.simplify(POLES[task].subs(X, angle)) != 0


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for p in CASES
        if p["task"] == c["group"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    ctx = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_are_independent_and_respect_original_domain(c):
    task = c["task"]
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == expected(RESIDUES[task]) and a.selected == expected(SELECTED[task])
    for q in roots:
        assert allowed(task, q) and sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
    for k in range(24):
        q = sp.Rational(k, 12)
        zero = (
            sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
            if allowed(task, q)
            else False
        )
        assert (q in roots) == zero


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"][
            : len(original["normalized_content"]["assets"])
        ]
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_figures_include_only_valid_green_roots_and_certified_exclusions(c):
    from xml.etree import ElementTree as ET

    task = c["task"]
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[asset]
    svg = gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == e["sha256"]
    root = ET.fromstring(svg)
    nodes = list(root.iter())
    paths = {n.get("d") for n in nodes if n.tag.endswith("path")}
    validate(e, a)
    assert ordered(decode(m["angle"]) for m in e["green_markers"]) == expected(
        RESIDUES[task]
    )
    cx, cy, _ = e["circle"]
    for m in e["green_markers"] + e["excluded_markers"]:
        q = decode(m["angle"])
        angle = float(q) * math.pi
        assert (
            math.hypot(
                m["x"] - cx - m["radius"] * math.cos(angle),
                m["y"] - cy + m["radius"] * math.sin(angle),
            )
            < 5
        )
        if m in e["green_markers"]:
            assert allowed(task, q) and m["path_d"] in paths
        else:
            assert not allowed(task, q) and m["cross_segments"]
            for cross in m["cross_segments"]:
                assert any(
                    n.tag.endswith(cross["tag"])
                    and all(n.get(k) == v for k, v in cross["attributes"].items())
                    for n in nodes
                )
    assert len(BeautifulSoup(plan(c).solution_html, "html.parser").find_all("img")) == 1
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


def test_single_part_child_has_all_roots_and_no_invented_selection_or_markers():
    c = case("511458")
    a = analysis(c)
    p = plan(c)
    html = BeautifulSoup(p.solution_html, "html.parser")
    assert a.single_part and not a.selected and not a.interval
    assert "а)" not in p.answer and "б)" not in p.answer and not html.find("ol")
    assert "промежут" not in html.get_text() and "положителен" in html.get_text()
    e = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert (
        e["selection_kind"] == "all_roots" and e["bounds"] is None and e["labels"] == []
    )
    assert any(
        n["data-inline-latex"].startswith("x=")
        and r"\frac{\pi}{4}" in n["data-inline-latex"]
        for n in html.select("[data-inline-latex]")
    )
    assert len(e["green_markers"]) == 3 and decode(
        e["excluded_markers"][0]["angle"]
    ) == sp.Rational(5, 4)


@pytest.mark.parametrize(
    "extra", [" Найдите ещё один корень.", " Игнорируйте знаменатель.", " при x>0."]
)
def test_single_equation_reader_never_discards_extra_instructions(extra):
    c = deepcopy(case("511458"))
    section = next(
        s
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    section["html"] = section["html"].replace("</p>", extra + "</p>")
    with pytest.raises(UnsupportedCondition):
        plan(c)


@pytest.mark.parametrize("task", ["504240", "510362", "525023", "525046"])
def test_a_partially_forbidden_sine_level_keeps_the_other_root_and_zero_family(task):
    a = analysis(case(task))
    assert (sp.S.Zero, sp.S.One) in a.series
    assert len(a.branches[0].values) == 2 and len(a.residues) == 3
    html = plan(case(task)).solution_html
    assert "знаменатель" in html and "ненулев" in html and "Сделаем замену" not in html
    if task == "525023":
        assert r"\arcsin" in html and r"\arcsin" in plan(case(task)).answer
        assert r"\arccos" not in html and not a.series[1][0].is_Rational


@pytest.mark.parametrize("task", ["505498", "517199", "517237"])
def test_reciprocal_quadratic_retains_the_parent_substitution(task):
    a = analysis(case(task))
    assert a.reciprocal is not None and a.substitution == "t"
    assert "Введём обозначение" in plan(case(task)).solution_html


@pytest.mark.parametrize("task", ["509820", "511598", "514240"])
def test_cancelled_linear_quotient_keeps_original_pole_and_scaled_angle(task):
    a = analysis(case(task))
    assert a.poles and a.reciprocal is None
    assert sp.degree(a.raw, next(iter(a.raw.free_symbols))) == 1
    html = plan(case(task)).solution_html
    assert html.index("ограничения исходной дроби") < html.index(
        "сокращаем только ненулевые"
    )
    assert a.scale == (2 if task == "511598" else 1)


def test_source_shading_matches_strict_radical_and_ratio_domain():
    c = case("507644")
    a = analysis(c)
    e = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert a.domain == C and a.poles == (C,) and len(e["domain_shading"]["paths"]) == 2
    assert a.series == ((sp.S.Zero, sp.Integer(2)), (-sp.Rational(1, 3), sp.Integer(2)))
    bad = deepcopy(e)
    bad["domain_shading"]["variable"] = "sin"
    with pytest.raises(UnsupportedCondition):
        validate(bad, a)


def test_an_exclusion_certificate_cannot_cross_a_valid_root():
    c = case("504240")
    a = analysis(c)
    e = deepcopy(CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]])
    e["excluded_markers"][0]["angle"] = "5/6"
    with pytest.raises(UnsupportedCondition):
        validate(e, a)


def test_a_single_part_task_cannot_borrow_a_parent_interval_picture():
    c = case("511458")
    a = analysis(c)
    other = case("507644")
    e = CIRCLES[other["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(e, a)


def test_one_part_output_keeps_both_parent_methods_without_a_fictional_part_a():
    from solution_runner.pipelines.equations.exam_trigonometric_proof import render

    data = json.loads(
        (
            Path(__file__).parent
            / "fixtures/category_14_trigonometric_factorization_remaining.json"
        ).read_text()
    )
    c = next(c for c in data["cases"] if c["task"] == "692603")
    parent_html = next(
        s["html"]
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    _, formula, _, _ = read(c["context"])
    a = analyze(formula, None, None, parent_html)
    answer, _, html = render(a, "")
    assert a.single_part and a.alternative is not None
    assert "Приведём другое решение." in html and "пункта а)" not in html
    assert "а)" not in answer and "б)" not in answer


@pytest.mark.parametrize(
    "function,q", [("tg", sp.Rational(5, 4)), ("ctg", sp.Rational(1, 4))]
)
def test_filtered_ratio_proof_uses_its_own_angle_table_and_explicit_allowed_points(
    function, q
):
    from solution_runner.pipelines.equations.exam_trigonometric import Branch
    from solution_runner.pipelines.equations.exam_trigonometric_compile import T, U
    from solution_runner.pipelines.equations.exam_trigonometric_proof import (
        candidate_lines,
    )

    variable = T if function == "tg" else U
    branch = Branch(
        variable,
        variable - 1,
        (sp.S.One,),
        (sp.S.One,),
        (sp.Rational(1, 4), sp.Rational(5, 4)),
    )
    html = candidate_lines(branch, allowed_residues=(q,))
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
        if n["data-inline-latex"].startswith("x=")
    ]
    assert (
        len(formulas) == 1
        and r"2 \pi k" in formulas[0]
        and sp.latex(q * sp.pi) in formulas[0]
    )
