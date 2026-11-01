"""Two original log domains, physical double angles and every native SVG marker."""

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
from solution_runner.pipelines.equations.exam_trigonometric_log_linear import branches
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_linear.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "542039": ((R(1, 12), R(5, 12)), (R(1, 12), R(5, 12))),
    "547301": ((R(1, 4),), (-R(7, 4),)),
    "622670": ((R(1, 12), R(5, 12)), (R(1, 12), R(5, 12))),
    "641097": ((R(1, 6), R(11, 6)), (-R(13, 6), -R(11, 6))),
    "673035": ((R(7, 6), R(11, 6)), (R(7, 6), R(11, 6))),
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
    si, co = sp.simplify(sp.sin(q * sp.pi)), sp.simplify(sp.cos(q * sp.pi))
    if key in ("542039", "622670"):
        return (
            sp.simplify(2 * si * co - R(1, 2)) == 0
            and sp.sin(q * sp.pi + 5 * sp.pi / 12).is_positive is True
            and sp.sin(q * sp.pi + sp.pi / 12).is_positive is True
        )
    if key == "547301":
        return sp.simplify(si - sp.sqrt(2) / 2) == 0 and co.is_positive is True
    if key == "641097":
        return (
            sp.simplify(co * co - R(3, 4)) == 0 and (co - R(1, 2)).is_positive is True
        )
    return sp.simplify(2 * si * si + si) == 0 and si.is_negative is True


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_both_original_logs(c):
    a = analysis(c)
    full, chosen = EXPECTED[c["task"]]
    assert a.scale == 1 and a.translation == 0
    assert select(a.series, (0, 2, True, False))[0] == full and a.selected == chosen
    for q in (*full, *chosen):
        assert original_zero(c["task"], sp.sympify(q))
    for q in (R(n, 24) for n in range(48)):
        assert original_zero(c["task"], q) == (q in full)
    assert len([p for p, rel in conditions(a) if rel == "positive"]) == 2


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_profiles_reuse_the_same_exact_catalogue_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_local_replay_keeps_sources(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    section(ctx["normalized_content"], "answer")["html"] = "<p>UNUSED 999</p>"
    section(ctx["normalized_content"], "solution")["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_all_original_svg_frames_roots_boundaries_and_excluded_points(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    points = [*e["green_markers"], *e["boundary_markers"], *e["excluded_markers"]]
    assert (
        len(points)
        == {"542039": 6, "547301": 3, "622670": 4, "641097": 4, "673035": 4}[c["task"]]
    )
    for f in e["native_frames"]:
        assert f["path_d"] in paths and f["rx"] > 30 and f["ry"] > 30
    for p in points:
        f = e["native_frames"][p["native_frame"]]
        q = float(sp.Rational(p["angle"]))
        xy = (
            f["cx"] + f["rx"] * math.cos(q * math.pi),
            f["cy"] - f["ry"] * math.sin(q * math.pi),
        )
        assert p["path_d"] in paths
        assert math.hypot(p["x"] - xy[0], p["y"] - xy[1]) < 1.6
    for p in e["excluded_markers"]:
        assert (
            failed(analysis(c), sp.Rational(p["angle"])) is not None
            and len(p["cross_segments"]) >= 2
        )
        for seg in p["cross_segments"]:
            assert any(dict(n.attrib) == seg["element"] for n in root.iter())
    assert not e.get("corrected_file")
    assert "/assets/" + aid in plan(c).solution_html


def test_css_defined_circle_and_small_native_blue_points_are_not_discarded():
    c = case("622670")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()).decode()
    assert ".st1{fill:none;stroke:#000000;" in raw
    root = ET.fromstring(raw)
    frame = CIRCLES[aid]["native_frames"][0]
    node = next(n for n in root.iter() if n.get("d") == frame["path_d"])
    assert node.get("class") and node.get("stroke") is None
    for key in ("542039", "547301"):
        c = case(key)
        e = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
        assert e["boundary_markers"]


@pytest.mark.parametrize("key", ["542039", "622670"])
def test_positive_product_does_not_admit_two_negative_original_arguments(key):
    a = analysis(case(key))
    d = a.log_product.equality.linear
    assert d.implication and d.projection == S / 2 - R(1, 4)
    source = branches(a, a.preferred, a.allow_inverse)
    assert (
        len(source) == 1
        and source[0].angle_scale == 2
        and source[0].residues == (R(1, 12), R(5, 12), R(13, 12), R(17, 12))
    )
    assert a.series == ((R(1, 12), 2), (R(5, 12), 2))
    for q in (R(13, 12), R(17, 12)):
        vals = [
            sp.simplify(p.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
            for p, rel in conditions(a)
            if rel == "positive"
        ]
        assert sp.simplify(vals[0] * vals[1]) == R(1, 2) and all(
            v.is_negative for v in vals
        )
        assert failed(a, q) is not None and q not in a.residues
    html = plan(case(key)).solution_html
    assert (
        html.index("Перейдём к следствию")
        < html.index("2x=")
        < html.index("Проверим представителей")
    )
    assert (
        r"\cos\left(\frac{\pi}{3}\right)-\cos\left(2 x + \frac{\pi}{2}\right)"
        in "".join(formulas(html))
    )


def test_parent_figure_stages_and_both_implication_checks_are_retained():
    c = case("542039")
    html = plan(c).solution_html
    assert (
        html.index("2x=") < html.index("<img") < html.index("Проверим представителей")
    )
    assert (
        BeautifulSoup(html, "html.parser").img.find_parent("li")["data-list-marker"]
        == "а)"
    )
    for key in ("547301", "622670", "673035"):
        html = plan(case(key)).solution_html
        assert BeautifulSoup(html, "html.parser").img.find_parent("li") is None
    c = case("641097")
    html = plan(c).solution_html
    assert (
        html.index("<img")
        < html.index("Сохраним условия")
        < html.index("объединим логарифмы")
    )


@pytest.mark.parametrize("key,var,sign", [("547301", C, ">0"), ("673035", S, "<0")])
def test_nonzero_factor_is_proved_from_original_domain_before_dividing(key, var, sign):
    a = analysis(case(key))
    assert a.log_product.divide == var
    f = formulas(plan(case(key)).solution_html)
    proof = next(i for i, t in enumerate(f) if r"\Longrightarrow" in t and r"\ne0" in t)
    from solution_runner.pipelines.equations.exam_trigonometric_proof import formula

    reduced = formula(sp.cancel(a.log_product.factor / var)) + "=0"
    assert proof < f.index(reduced)
    assert sign in f[proof]


def test_reciprocal_base_and_large_exact_phase_keep_actual_base_conversion():
    first = analysis(case("547301"))
    assert first.log_product.equality.linear.multipliers == (1, -1)
    second = analysis(case("673035"))
    assert (
        second.log_product.equality.linear.multipliers == (1, 2)
        and second.log_product.equality.linear.common == 2
    )
    assert second.series == ((-R(1, 6), 2), (-R(5, 6), 2))
    assert any(
        "2025" in t and "=-" in t for t in formulas(plan(case("673035")).solution_html)
    )
    assert failed(second, sp.S.Zero) is not None and 0 not in second.residues


def test_domain_first_cosine_product_rejects_the_negative_square_root():
    a = analysis(case("641097"))
    assert a.log_product.equality.linear.domain_first
    assert failed(a, R(5, 6)) is not None and failed(a, R(7, 6)) is not None
    html = plan(case("641097")).solution_html
    f = formulas(html)
    assert r"(\cos x)>\frac{1}{2}" in f
    assert any(r"- \frac{\sqrt{3}}{2}" in t for t in f)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_extra_instruction_and_changed_interval_fail_closed(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    sec["html"] += "<p>Ещё найдите приближённые корни.</p>"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    s = BeautifulSoup(sec["html"], "html.parser")
    s.select("[data-inline-latex]")[-1]["data-inline-latex"] = "[-10;10]"
    sec["html"] = str(s)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


def test_compatible_common_base_change_reuses_exact_existing_svg():
    c = case("641097")
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    sec["html"] = (
        sec["html"].replace(r"\log_2", r"\log_4").replace("=-1", r"=-\frac{1}{2}")
    )
    a = analysis(c, ctx)
    assert a.selected == (-R(13, 6), -R(11, 6))
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )
    assert (
        c["context"]["normalized_content"]["assets"][0]["asset_id"]
        in plan(c, ctx).solution_html
    )


def test_almost_closed_blue_circle_uses_native_extrema_not_a_tiny_diameter():
    c = case("547301")
    e = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    f = next(f for f in e["native_frames"] if f["path_d"].startswith("M55.867,110.994"))
    assert f["kind"] == "full_extrema" and 48 < f["rx"] < 49 and 48 < f["ry"] < 49


def test_product_to_sum_method_does_not_publish_internal_unit_circle_expansion():
    for key in ("542039", "622670"):
        f = formulas(plan(case(key)).solution_html)
        assert not any(r"(\cos x)" in x or r"(\sin x)" in x for x in f)
        assert any(r"\cos\left(2 x + \frac{\pi}{2}\right)=-" in x for x in f)


def test_equal_log_arguments_are_compared_directly_after_base_change():
    f = formulas(plan(case("673035")).solution_html)
    assert not any(r"/\left(" in x for x in f)
    assert any(x.count(r"\log_{2025}") == 2 and "=" in x for x in f)
