"""Parent log cases, denominator-only logs, exact domains and original figure roles."""

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
from solution_runner.pipelines.equations.exam_trigonometric_proof import formula
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_remaining_log_products.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "696038": ((R(3, 2), R(23, 12)), (-R(5, 2), -R(25, 12))),
    "516331": ((R(1, 6),), (-R(23, 6),)),
    "516298": ((R(1, 6),), (-R(11, 6),)),
    "484556": ((R(3, 2), R(5, 3)), (R(3, 2), R(5, 3))),
    "628134": ((R(11, 6),), (R(11, 6),)),
    "629503": ((sp.S.Zero,), (-sp.Integer(2),)),
    "633979": ((R(5, 6),), (-R(31, 6),)),
    "640574": ((R(5, 6),), (-R(31, 6),)),
    "646757": ((sp.S.Zero, R(11, 6)), (-R(13, 6), -sp.Integer(2))),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original(key, q):
    angle = float(q) * math.pi
    si, co = math.sin(angle), math.cos(angle)
    si = 0 if abs(si) < 1e-12 else si
    co = 0 if abs(co) < 1e-12 else co
    if key == "696038":
        return si < 0 and (
            abs(2 * si + 2 * math.cos(angle + math.pi / 6) - math.sqrt(2)) < 1e-9
            or abs(-si - 1) < 1e-9
        )
    if key == "484556":
        return si < 0 and (abs(2 * co * co - 5 * co + 2) < 1e-9 or abs(-si - 1) < 1e-9)
    if key in ("633979", "640574"):
        return co < 0 and (
            abs(-2 * co * co + si + 1) < 1e-9 or abs(-0.8 * co - 1) < 1e-9
        )
    if key == "646757":
        return co > 0 and (abs(8 * si * si + 14 * si + 5) < 1e-9 or abs(co - 1) < 1e-9)
    if key == "516298":
        return (
            si > 0
            and abs(si - 1) > 1e-9
            and abs(2 * co * co - math.sqrt(3) * co) < 1e-9
        )
    if key == "516331":
        return co > 0 and abs(co - 1) > 1e-9 and abs(2 * si * si - si) < 1e-9
    if key == "628134":
        return co > 0 and abs(co - 1) > 1e-9 and abs(2 * si * si - si - 1) < 1e-9
    if key == "629503":
        return (
            co + 1 > 1e-9
            and abs(co) > 1e-9
            and abs(math.sin(2 * angle) * math.cos(2 * angle) + 2 * math.sin(2 * angle))
            < 1e-9
        )
    raise AssertionError(key)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_the_original_equation_and_log_domain(c):
    a = analysis(c)
    full, selected = EXPECTED[c["task"]]
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == selected
    for q in (*full, *selected):
        assert original(c["task"], q)
    for k in range(-144, 145):
        q = R(k, 24)
        assert original(c["task"], q) == (q % 2 in full), (c["task"], q)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_reuses_the_shared_runner(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], g["theme_order"], g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    before = deepcopy(c["context"])
    p = plan(c)
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = (
            "<p>Не использовать сохранённые числа.</p>"
        )
    assert plan(c, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert key.startswith("section:") and not key.startswith("section:condition")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_svg_bytes_native_markers_and_crosses_match_the_domain(c):
    a = analysis(c)
    for asset in c["context"]["normalized_content"]["assets"]:
        aid = asset["asset_id"]
        entry = CIRCLES[aid]
        raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        paths = {
            n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")
        }
        assert entry["native_circle_path"] in paths
        for point in (*entry["green_markers"], *entry["excluded_markers"]):
            assert point["path_d"] in paths
            q = R(point["angle"])
            cx, cy, radius = entry["circle"]
            radius = point.get("radius", radius)
            assert (
                math.hypot(
                    point["x"] - cx - radius * math.cos(float(q) * math.pi),
                    point["y"] - cy + radius * math.sin(float(q) * math.pi),
                )
                < 5
            )
            assert original(c["task"], q) == (point in entry["green_markers"])
        validate(
            entry,
            a
            if entry.get("selection_kind") == "all_roots"
            else replace(a, image_position="selection"),
        )


@pytest.mark.parametrize("key", ["516331", "516298", "628134", "629503"])
def test_denominator_only_logarithm_does_not_create_a_numerator_log_zero_case(key):
    a = analysis(case(key))
    assert a.log_product.base is None and a.log_product.argument is None
    assert a.log_product.denominator is not None
    f = formulas(plan(case(key)).solution_html)
    assert not any(x.startswith(r"\log_") and x.endswith("=0") for x in f)
    assert any(x.startswith(r"\log_") and r"\ne0" in x for x in f)


@pytest.mark.parametrize("key", ["696038", "484556"])
def test_parent_log_zero_case_precedes_the_algebraic_case(key):
    a = analysis(case(key))
    assert a.log_product.log_first
    html = plan(case(key)).solution_html
    assert html.index("Логарифм с допустимым") < html.index(
        "Теперь рассмотрим случай ненулевого"
    )
    assert any(R(3, 2) in b.residues for b in a.branches)
    assert R(3, 2) in EXPECTED[key][0]


def test_bounded_nonzero_log_and_impossible_log_zero_keep_different_parent_methods():
    impossible = plan(case("633979")).solution_html
    nonzero = plan(case("640574")).solution_html
    assert analysis(case("640574")).log_product.nonzero_bound == R(4, 5)
    assert "наибольшее значение" in nonzero and "Разделим на него" in nonzero
    assert "Логарифм с допустимым" not in nonzero
    assert any(x.endswith("=" + sp.latex(-R(5, 4))) for x in formulas(impossible))
    assert (
        "не имеет" in BeautifulSoup(impossible, "html.parser").get_text()
        or "корней не имеет" in impossible
    )
    assert "Логарифм с допустимым" in impossible
    for html in (impossible, nonzero):
        assert formula(C**2) + "=" + formula(1 - S**2) in formulas(html)
        assert formula(2 * S * S + S - 1) + "=0" in formulas(html)
        f = formulas(html)
        assert f.index(formula(S) + "=-1") < f.index(
            formula(S) + "=" + sp.latex(R(1, 2))
        )


def test_auxiliary_angle_follows_the_original_cosine_sum_and_preserves_two_letters():
    c = case("696038")
    a = analysis(c)
    html = plan(c).solution_html
    f = formulas(html)
    assert any(r"\cos x\cos\left(" in x and r"\sin x\sin\left(" in x for x in f)
    assert "сдвинутого угла" in html
    assert a.series == ((-R(1, 2), sp.Integer(2)), (-R(1, 12), sp.Integer(2)))
    assert a.family_parameters == ("k", "n")
    assert any(r"n\in\mathbb Z" in x for x in f)


def test_double_angle_numerator_keeps_its_positive_remaining_factor():
    a = analysis(case("629503"))
    assert a.log_product.double_angle == (2, 2)
    html = plan(case("629503")).solution_html
    f = formulas(html)
    assert any(
        r"\sin\left(2 x\right)\left(\cos\left(2 x\right)+2\right)=0" == x for x in f
    )
    assert any(r"\cos\left(2 x\right)+2\ge 1>0" == x for x in f)
    assert any(r"x=\frac{\pi k}{2}" in x for x in f)
    assert html.count("эту серию исключаем") == 3


def test_parent_two_figures_and_child_one_figure_keep_the_original_inventory():
    p = BeautifulSoup(plan(case("516331")).solution_html, "html.parser")
    images = p.find_all("img")
    assert [i["data-asset-key"] for i in images] == ["image_1", "image_2"]
    assert all(i.find_parent("li")["data-list-marker"] == "а)" for i in images)
    first_part = p.select_one('li[data-list-marker="а)"]')
    assert str(first_part).index('data-asset-key="image_1"') < str(first_part).index(
        'data-asset-key="image_2"'
    )
    assert any(r"\quad(*)" in f for f in formulas(str(p)))
    assert any(r"\quad(**)" in f for f in formulas(str(p)))
    child = BeautifulSoup(plan(case("516298")).solution_html, "html.parser")
    assert len(child.find_all("img")) == 1
    assert analysis(case("516298")).series == ((R(1, 6), sp.Integer(2)),)
    assert analysis(case("516298")).selected == (-R(11, 6),)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_or_extra_condition_fails_closed(c):
    context = deepcopy(c["context"])
    section(context["normalized_content"], "condition")["html"] += (
        "<p>Затем вычислите произведение всех корней.</p>"
    )
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
    if c["context"]["normalized_content"]["assets"]:
        context = deepcopy(c["context"])
        context["normalized_content"]["assets"][0]["asset_id"] = "unknown"
        with pytest.raises(UnsupportedCondition):
            plan(c, context)


@pytest.mark.parametrize("key", ["696038", "646757"])
def test_each_integer_parameter_is_bound_in_intermediate_and_final_families(key):
    import re

    for text in formulas(plan(case(key)).solution_html):
        if text.startswith("x=") and r"\in\mathbb Z" in text:
            left, _, right = text.partition(r"\quad")
            used = set(re.findall(r"(?<![A-Za-z\\])[kn](?![A-Za-z])", left))
            bound = set(re.findall(r"(?<![A-Za-z\\])[kn](?![A-Za-z])", right))
            assert used <= bound, text


@pytest.mark.parametrize(
    "key,variable,first,second",
    [
        ("646757", S, -R(1, 2), -R(5, 4)),
        ("628134", S, sp.S.One, -R(1, 2)),
        ("516331", S, sp.S.Zero, R(1, 2)),
        ("516298", C, sp.S.Zero, sp.sqrt(3) / 2),
    ],
)
def test_quadratic_candidates_follow_the_order_of_the_parent(
    key, variable, first, second
):
    f = formulas(plan(case(key)).solution_html)
    assert f.index(formula(variable) + "=" + sp.latex(first)) < f.index(
        formula(variable) + "=" + sp.latex(second)
    )


def test_an_altered_denominator_log_cannot_reuse_the_original_domain_figure():
    c = case("516331")
    a = analysis(c)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    changed = replace(a, log_product=replace(a.log_product, denominator=(7, 2 * C)))
    with pytest.raises(UnsupportedCondition):
        validate(entry, changed)
