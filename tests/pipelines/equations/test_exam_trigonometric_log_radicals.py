"""Original radical-log products, strict poles, two source methods and native figures."""

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
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    branches,
    conditions,
    failed,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_radical import (
    compile_product,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_radicals.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "700451": ((R(2, 3),), (-R(4, 3),)),
    "632828": ((R(1, 3), R(7, 4)), (-R(9, 4), -R(5, 3))),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    x = float(q) * math.pi
    si, co = math.sin(x), math.cos(x)
    rad = 2 * si + math.sqrt(2)
    if key == "700451":
        if abs(co) < 1e-10 or -2 * co <= 0 or -si / co <= 1e-10 or rad < -1e-10:
            return False
        return (
            abs(math.sqrt(max(0, rad)) * math.log(-2 * co, 3) / math.sqrt(-si / co))
            < 1e-8
        )
    if 2 * co <= 1e-10 or rad < -1e-10:
        return False
    return abs(math.sqrt(max(0, rad)) * math.log(2 * co, 4)) < 1e-8


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_the_original_roots_and_log_domains(c):
    a = analysis(c)
    full, selected = EXPECTED[c["task"]]
    assert select(a.series, (0, 2, True, False))[0] == full and a.selected == selected
    for q in (*full, *selected):
        assert original_zero(c["task"], q)
    for q in (R(n, 24) for n in range(-144, 145)):
        assert original_zero(c["task"], q) == (q % 2 in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_profiles_extend_the_existing_shared_runner(g):
    p = get_group_profile(g["key"])
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert p.group_order_index == g["order"] and p.theme_order_index == g["theme_order"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_all_original_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    section(ctx["normalized_content"], "answer")["html"] = "<p>Wrong saved answer</p>"
    section(ctx["normalized_content"], "solution")["html"] = (
        "<p>Unused child solution</p>"
    )
    actual = plan(c, ctx)
    assert actual == plan(c)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in actual.transformations
    )
    for t in actual.transformations:
        target = next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s.get("transformation_target_id") == t["transformation_target_id"]
        )
        target.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert before == c["context"]


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_all_original_svg_bytes_paths_and_native_markers_match_the_original_domain(c):
    for asset in c["context"]["normalized_content"]["assets"]:
        aid = asset["asset_id"]
        entry = CIRCLES[aid]
        raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        tree = ET.fromstring(raw)
        paths = {n.get("d") for n in tree.iter() if n.tag.endswith("path")}
        assert entry["native_circle_path"] in paths
        for p in (*entry["green_markers"], *entry["excluded_markers"]):
            assert p["path_d"] in paths
            q = R(p["angle"])
            cx, cy, r = entry["circle"]
            r = p.get("radius", r)
            assert (
                math.hypot(
                    p["x"] - cx - r * math.cos(float(q) * math.pi),
                    p["y"] - cy + r * math.sin(float(q) * math.pi),
                )
                < 2
            )
            assert original_zero(c["task"], q) == (p in entry["green_markers"])


def test_zero_numerator_root_is_retained_but_a_zero_denominator_root_is_forbidden():
    a = analysis(case("632828"))
    assert failed(a, R(7, 4)) is None
    b = analysis(case("700451"))
    assert (b.log_product.radical.denominator, "positive") in conditions(b)
    rejected = failed(b, sp.S.One)
    assert rejected[1:] == ("positive", sp.S.Zero)
    assert failed(b, R(1, 2)) is not None and failed(b, R(4, 3)) is not None


def test_the_nonstrict_radical_rejection_is_not_printed_as_a_zero_denominator():
    f = formulas(plan(case("632828")).solution_html)
    assert any(r"\not\ge0" in x for x in f)
    assert any(r"\sin x\ge" in x for x in f)


def test_cancelling_radicals_follows_the_strict_domain_and_does_not_create_a_zero_case():
    c = case("700451")
    a = analysis(c)
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    part = soup.select_one('li[data-list-marker="а)"]')
    assert a.log_product.radical.divide and len(a.branches) == 1
    f = formulas(str(part))
    assert r"\sin x" in f[0] and r"\ge0" in f[0]
    assert r"\cos x" in f[1] and f[1].endswith(">0")
    assert r"\tg x" in f[2] and f[2].endswith(">0")
    html = str(part)
    assert (
        html.index("строго положительны")
        < html.index("<img")
        < html.index("Логарифм равен нулю")
    )
    assert "корень равен нулю" not in html and "иначе" not in html
    assert len(part.find_all("img")) == 1 and not soup.select(
        'li[data-list-marker="б)"] img'
    )


def test_both_parent_methods_and_each_figure_keep_their_original_subparts_and_order():
    c = case("632828")
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    a = soup.select_one('li[data-list-marker="а)"]')
    b = soup.select_one('li[data-list-marker="б)"]')
    assert (
        a.find_all("img")[0]["data-asset-key"] == "image_1"
        and b.find_all("img")[0]["data-asset-key"] == "image_2"
    )
    assert (
        str(a).index("<img")
        < str(a).index("Найдём область")
        < str(a).index("произведение равно нулю")
    )
    assert (
        str(b).index("отберём корни")
        < str(b).index("Изложим решение пункта а) иначе")
        < str(b).index("<img")
        < str(b).index("отдельно для каждого")
    )
    assert len(a.find_all("img")) == len(b.find_all("img")) == 1
    for part in (a, b):
        assert "корень равен нулю" in str(part) and "Логарифм равен нулю" in str(part)
        assert r"\not\ge0" in str(part) and r"\not&gt;0" in str(part)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_compatible_original_circles_are_reused_without_generated_or_added_assets(c):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert h.diagram_specs(c["context"]) == ()
    p = plan(c)
    assert not any(
        t["transformation_target_id"].startswith("asset:") for t in p.transformations
    )
    soup = BeautifulSoup(p.solution_html, "html.parser")
    assert [
        (n["data-asset-key"], n["data-asset-id"]) for n in soup.find_all("img")
    ] == [
        (a["asset_key"], a["asset_id"])
        for a in c["context"]["normalized_content"]["assets"]
    ]


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_circle_changed_interval_or_extra_instruction_fail_closed(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    s["html"] = s["html"].replace(r"-\pi]", r"0]")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += (
        "<p>И ещё найдите приближённые корни.</p>"
    )
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


def test_changed_parameters_use_the_same_certificate_and_recompute_all_zero_cases():
    e = compile_product(r"\sqrt{4\sin x+2}\log_7(2\cos x)=0", parent(case("632828")))
    residues = tuple(sorted({q for b in branches(e, C) for q in b.residues}))
    assert residues == (R(1, 3), R(11, 6))
    e = compile_product(
        r"\frac{\sqrt{7\sin x+5}\log_{\frac{1}{2}}(-\sqrt{2}\cos x)}{\sqrt{-2\tg x}}=0",
        parent(case("700451")),
    )
    assert e.log_product.radical.divide
    assert tuple(q for b in branches(e, C) for q in b.residues) == (R(3, 4),)


def test_a_cancelled_original_ratio_pole_is_still_an_original_domain_restriction():
    e = compile_product(
        r"\frac{\sin x}{\sin x}\sqrt{2\sin x+\sqrt{2}}\log_4(2\cos x)=0",
        parent(case("632828")),
    )
    assert S in e.poles and failed(e, sp.S.Zero) is not None
