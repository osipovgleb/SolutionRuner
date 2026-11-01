"""Original log domains, parent zero-factor methods and separate source-circle roles."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from dataclasses import replace
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
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_products.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
FULL = {
    "648771": (R(1, 4), R(7, 6), R(5, 4)),
    "655320": (R(2, 3), R(3, 4), R(7, 4)),
    **{key: (R(5, 3),) for key in ("658806", "515648", "528869", "645663")},
}
SELECTED = {
    "648771": (R(9, 4), R(19, 6), R(13, 4)),
    "655320": (-R(9, 4), -R(4, 3), -R(5, 4)),
    "658806": (-R(1, 3),),
    "515648": (R(5, 3),),
    "528869": (-R(1, 3),),
    "645663": (-R(7, 3), -R(1, 3)),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


def original(key, q):
    si, co = sp.simplify(sp.sin(q * sp.pi)), sp.simplify(sp.cos(q * sp.pi))
    if co == 0:
        return False
    if key == "648771":
        argument = sp.simplify(si / co)
        return argument > 0 and (
            sp.simplify(2 * co**2 + sp.sqrt(3) * co) == 0 or argument == 1
        )
    if key == "655320":
        argument = sp.simplify(-si / co)
        return argument > 0 and (
            sp.simplify(sp.sqrt(3) * si - 2 * si**2) == 0 or argument == 1
        )
    if si == 0 or co < 0 or sp.simplify(sp.sqrt(2) * co - 1) == 0:
        return False
    return sp.simplify(si / co + sp.sqrt(3)) == 0 or sp.simplify(2 * si**2 - 1) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_original_log_arguments_and_denominator(c):
    a = analysis(c)
    assert select(a.series, (0, 2, True, False))[0] == FULL[c["task"]]
    assert a.selected == SELECTED[c["task"]]
    for q in set(FULL[c["task"]]) | {R(k, 24) for k in range(48)}:
        assert original(c["task"], q) == (q in FULL[c["task"]])
    assert all(original(c["task"], q) for q in a.selected)
    assert a.log_product is not None


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_reuses_the_common_runner(g):
    p = get_group_profile(g["key"])
    assert p.source_group_id == g["uuid"]
    assert p.snapshot_theme_id == g["theme_uuid"]
    assert p.group_order_index == g["order"]
    assert p.theme_order_index == g["theme_order"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    p = plan(c)
    context = deepcopy(c["context"])
    original_condition = deepcopy(section(context["normalized_content"], "condition"))
    original_assets = deepcopy(context["normalized_content"]["assets"])
    for key in ("answer", "solution"):
        section(context["normalized_content"], key)["html"] = (
            "<p>Не использовать сохранённые числа: 997.</p>"
        )
    assert plan(c, context) == p
    updated = deepcopy(c["context"])
    for transformation in p.transformations:
        target = transformation["transformation_target_id"]
        assert target.startswith("section:") and not target.startswith(
            "section:condition"
        )
        next(
            s
            for s in updated["normalized_content"]["sections"]
            if s["transformation_target_id"] == target
        ).update(transformation["value"])
    assert plan(c, updated).transformations == ()
    assert section(updated["normalized_content"], "condition") == original_condition
    assert updated["normalized_content"]["assets"] == original_assets
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_all_original_svg_bytes_native_points_and_crossed_candidates_match(c):
    a = analysis(c)
    for asset in c["context"]["normalized_content"]["assets"]:
        aid = asset["asset_id"]
        e = CIRCLES[aid]
        data = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        assert hashlib.sha256(data).hexdigest() == e["sha256"]
        root = ET.fromstring(data)
        paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
        assert e["native_circle_path"] in paths
        for point in (*e["green_markers"], *e["excluded_markers"]):
            assert point["path_d"] in paths
            q = R(point["angle"])
            cx, cy, radius = e["circle"]
            radius = point.get("radius", radius)
            assert (
                math.hypot(
                    point["x"] - cx - radius * math.cos(float(q) * math.pi),
                    point["y"] - cy + radius * math.sin(float(q) * math.pi),
                )
                < 5
            )
            assert original(c["task"], q) == (point in e["green_markers"])
        validate(
            e,
            a
            if e.get("selection_kind") == "all_roots"
            else replace(a, image_position="selection"),
        )


@pytest.mark.parametrize("key", ["658806", "515648", "528869", "645663"])
def test_numerator_log_zero_candidates_are_all_forbidden_by_the_original_denominator(
    key,
):
    a = analysis(case(key))
    assert a.log_product.denominator[0] == (47 if key == "528869" else 31)
    assert any(not b.residues for b in a.branches)
    for q in (R(1, 4), R(3, 4), R(5, 4), R(7, 4)):
        assert not original(key, q)
    html = plan(case(key)).solution_html
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any(r"\log_{13}" in f and f.endswith("=0") for f in formulas)
    assert any(
        r"\log_{" + str(a.log_product.denominator[0]) + "}" in f and r"\ne0" in f
        for f in formulas
    )
    assert not any("D=" in f for f in formulas)


def test_parent_division_and_parent_zero_sine_case_remain_different_methods():
    cosine = case("648771")
    sine = case("655320")
    assert analysis(cosine).log_product.divide == C
    assert analysis(sine).log_product.divide == 1
    c_html = plan(cosine).solution_html
    s_html = plan(sine).solution_html
    assert "разделим обе части" in c_html
    assert "на тригонометрический множитель не делим" in s_html
    assert "D=" not in c_html + s_html
    assert any(b.variable == S and 0 in b.candidates for b in analysis(sine).branches)
    assert "не подходит" in s_html


def test_two_original_circles_stay_in_their_own_derivation_and_selection_parts():
    soup = BeautifulSoup(plan(case("655320")).solution_html, "html.parser")
    images = soup.find_all("img")
    assert [i["data-asset-key"] for i in images] == ["image_1", "image_2"]
    assert [i.find_parent("li")["data-list-marker"] for i in images] == ["а)", "б)"]


@pytest.mark.parametrize("key", ["658806", "528869"])
def test_full_root_circle_is_not_reinterpreted_as_interval_selection(key):
    c = case(key)
    a = analysis(c)
    assert a.selection_method == "inequalities"
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert soup.find("img").find_parent("li")["data-list-marker"] == "а)"
    assert "неравенств" in soup.get_text()
    assert not soup.select('li[data-list-marker="б)"] img')
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(entry, replace(a, image_position="selection"))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_and_unrecognized_instruction_are_rejected(c):
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += (
        "<p>Дополнительно вычислите сумму квадратов корней.</p>"
    )
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    if c["context"]["normalized_content"]["assets"]:
        ctx = deepcopy(c["context"])
        ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
        with pytest.raises(UnsupportedCondition):
            plan(c, ctx)


def test_open_interval_and_independent_integer_name_are_preserved():
    a = analysis(case("528869"))
    assert a.bounds == (-R(1, 2), R(1, 2), False, False)
    html = plan(case("515648")).solution_html
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any("x=" in f and r"n\in\mathbb Z" in f for f in formulas)
    assert analysis(case("515648")).parameter == "n"


@pytest.mark.parametrize("key", ["658806", "528869"])
def test_derivation_figure_remains_compatible_when_only_selection_bounds_change(key):
    c = case(key)
    a = analysis(c)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    validate(entry, replace(a, bounds=(-4, 4, True, True), selected=()))
    assert entry["bounds"] is None and entry["labels"] == []


@pytest.mark.parametrize("key", ["648771", "515648"])
def test_interval_figure_cannot_reuse_old_labels_for_changed_selection_bounds(key):
    c = case(key)
    a = analysis(c)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(entry, replace(a, bounds=(-4, 4, True, True), selected=()))


def test_a_changed_log_domain_cannot_reuse_the_original_circle_certificate():
    c = case("528869")
    a = analysis(c)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    changed = replace(a, log_product=replace(a.log_product, argument=3 * S**2))
    with pytest.raises(UnsupportedCondition):
        validate(entry, changed)


def test_zero_sine_case_precedes_the_other_algebraic_level_as_in_the_parent():
    from solution_runner.pipelines.equations.exam_trigonometric_proof import formula

    soup = BeautifulSoup(plan(case("655320")).solution_html, "html.parser")
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert formulas.index(formula(S) + "=0") < formulas.index(
        formula(S) + "=" + sp.latex(sp.sqrt(3) / 2)
    )
