"""Common log definitions and powers retain native figures and parent methods."""

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
from solution_runner.pipelines.equations.exam_trigonometric_log_polynomial import L
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_powers.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "500447": ((R(1, 2), R(7, 6), R(3, 2), R(11, 6)), (R(3, 2), R(11, 6), R(5, 2))),
    "500467": ((0, R(2, 3), 1, R(4, 3)), (-4, -R(10, 3), -3, -R(8, 3))),
    "501480": (
        (R(1, 6), R(1, 2), R(5, 6), R(3, 2)),
        (R(13, 6), R(5, 2), R(17, 6), R(7, 2)),
    ),
    "508317": (
        (R(1, 6), R(1, 2), R(5, 6), R(3, 2)),
        (R(13, 6), R(5, 2), R(17, 6), R(7, 2)),
    ),
    "630105": ((R(1, 6), R(5, 6)), (R(13, 6),)),
    "641932": ((R(1, 3), R(5, 3)), (R(5, 3),)),
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


def generated(c, context=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(context or c["context"])
    )


def plan(c, context=None, prototype=None, assets=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
            generated_solution_assets=generated(c, context)
            if assets is None
            else assets,
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    si, co = sp.simplify(sp.sin(q * sp.pi)), sp.simplify(sp.cos(q * sp.pi))
    if key in ("630105", "641932"):
        v = si if key == "630105" else co
        # 2 log_2(v)^2+log_2(v)-1=0 gives v=1/2 or sqrt2; sqrt2>1.
        return v.is_positive is True and sp.simplify(v - R(1, 2)) == 0
    p = {
        "500447": co + 2 * si * co,
        "500467": si + 2 * si * co,
        "501480": co - 2 * si * co,
        "508317": 2 * si * co - co,
    }[key]
    return sp.simplify(p) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_original_logarithms_and_powers(c):
    a = analysis(c)
    full, chosen = EXPECTED[c["task"]]
    assert select(a.series, (0, 2, True, False))[0] == full and a.selected == chosen
    for q in (*full, *chosen):
        assert original_zero(c["task"], sp.sympify(q))
    for q in (R(n, 24) for n in range(48)):
        assert original_zero(c["task"], q) == (q in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_profiles_extend_the_existing_shared_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], g["theme_order"], g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_local_replay_preserves_original_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    section(ctx["normalized_content"], "answer")["html"] = "<p>UNUSED 999</p>"
    section(ctx["normalized_content"], "solution")["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        key = t["transformation_target_id"]
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next(
            (v for v in items if v.get("transformation_target_id") == key), None
        )
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        ctx["normalized_content"]["assets"][
            : len(before["normalized_content"]["assets"])
        ]
        == before["normalized_content"]["assets"]
    )
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
        and c["context"] == before
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_svg_hash_frames_and_every_colored_marker_are_preserved(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    for f in e["native_frames"]:
        assert f["path_d"] in paths and f["rx"] > 30 and f["ry"] > 30
    for m in [*e["green_markers"], *e["boundary_markers"]]:
        f = e["native_frames"][m["native_frame"]]
        q = float(sp.Rational(m["angle"]))
        expected = (
            f["cx"] + f["rx"] * math.cos(q * math.pi),
            f["cy"] - f["ry"] * math.sin(q * math.pi),
        )
        assert m["path_d"] in paths
        assert math.hypot(m["x"] - expected[0], m["y"] - expected[1]) < 1.7
    if c["task"] == "630105":
        assert e["point_scope"] == "selected" and e["complete_residues"] == [
            "1/6",
            "5/6",
        ]


def test_child_sine_common_factor_stays_before_cosine_level():
    p = plan(case("500467"))
    f = formulas(p.solution_html)
    assert f.index(r"(\sin x)=0") < f.index(r"(\cos x)=- \frac{1}{2}")
    assert p.answer.index(r"\pi k") < p.answer.index(r"\frac{2 \pi}{3}")
    assert r"(-1)" not in plan(case("508317")).answer


def test_log_powers_keep_substitution_and_actual_original_image_stages():
    first = case("630105")
    a = analysis(first)
    p = plan(first)
    f = formulas(p.solution_html)
    assert (
        a.log_polynomial.polynomial == 2 * L * L + L - 1
        and a.log_polynomial.powers.base == 5
    )
    assert (
        a.log_polynomial.substitution == "t" and a.log_polynomial.powers.image_after_log
    )
    image = p.solution_html.index("<img")
    assert (
        p.solution_html.index("t=-1")
        < image
        < p.solution_html.index("Вернёмся к исходной")
    )
    second = case("641932")
    a = analysis(second)
    p = plan(second)
    assert (
        a.log_polynomial.substitution is None
        and not a.log_polynomial.powers.image_after_log
    )
    assert p.solution_html.index("<img") < p.solution_html.index(
        "Перейдём к одному основанию"
    )
    assert "t=" not in "".join(formulas(p.solution_html))
    assert sum("^{" in q and ">0" in q for q in f) >= 1


def test_endpoint_label_correction_changes_only_three_native_elements():
    c = case("641932")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()).decode()
    fixed = (DIRECTORY / e["corrected_file"]).read_text()
    assert hashlib.sha256(fixed.encode()).hexdigest() == e["corrected_sha256"]
    r = e["correction"]
    old = ET.fromstring(raw)
    new = ET.fromstring(fixed)
    oldpaths = [n for n in old.iter() if n.tag.endswith("path")]
    newpaths = [n for n in new.iter() if n.tag.endswith("path")]
    assert len(oldpaths) == len(newpaths) + 1
    removed = next(n for n in oldpaths if n.get("d") == r["removed_digit_path"])
    oldpaths.remove(removed)
    for a, b in zip(oldpaths, newpaths, strict=True):
        if a.get("d") == r["pi_path"]:
            assert set(b.attrib) - set(a.attrib) == {"transform"}
            assert b.get("transform").startswith("translate(")
        else:
            assert a.attrib == b.attrib
    assert r["from_label"] == "5pi/2" and r["to_label"] == "pi/2"
    # Reverse the two replacements and the one removal to prove every other byte identical.
    import re

    five = next(
        m[0]
        for m in re.finditer(r'<path\b[^>]*d="([^"]+)"[^>]*/>', raw)
        if m[1] == r["removed_digit_path"]
    )
    pi = next(
        m[0]
        for m in re.finditer(r'<path\b[^>]*d="([^"]+)"[^>]*/>', raw)
        if m[1] == r["pi_path"]
    )
    changed = next(
        m[0]
        for m in re.finditer(r'<path\b[^>]*d="([^"]+)"[^>]*/>', fixed)
        if m[1] == r["pi_path"]
    )
    rebuilt = fixed.replace(changed, pi, 1).replace(
        r["new_fraction_line"], r["old_fraction_line"], 1
    )
    prefix = raw[: raw.index(five)]
    assert rebuilt.replace(prefix, prefix + five, 1) == raw
    assert len(generated(c)) == 1 and len(generated(case("630105"))) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_assets_and_changed_bounds_cannot_reuse_original_figures(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    soup = BeautifulSoup(sec["html"], "html.parser")
    soup.select("[data-inline-latex]")[-1]["data-inline-latex"] = "[-10;10]"
    sec["html"] = str(soup)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_instructions_and_extra_parent_methods_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c) + "<p>Другое решение.</p>")
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    sec["html"] = sec["html"].replace("Ре\xadши\xadте", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


def test_compatible_outer_base_change_reuses_existing_svg_exactly():
    c = case("630105")
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    sec["html"] = sec["html"].replace("5^", "125^").replace(r"\frac{5}", r"\frac{125}")
    a = analysis(c, ctx)
    assert a.log_polynomial.powers.base == 125 and a.selected == (R(13, 6),)
    assert (
        generated(c, ctx) == ()
        and "/assets/" + c["context"]["normalized_content"]["assets"][0]["asset_id"]
        in plan(c, ctx).solution_html
    )


def test_reciprocal_outer_base_keeps_the_same_exact_log_polynomial_and_svg():
    c = case("630105")
    ctx = deepcopy(c["context"])
    sec = section(ctx["normalized_content"], "condition")
    sec["html"] = (
        sec["html"]
        .replace("5^", r"(\frac{1}{5})^")
        .replace(r"\frac{5}", r"\frac{\frac{1}{5}}")
    )
    a = analysis(c, ctx)
    assert a.log_polynomial.powers.base == R(1, 5) and a.selected == (R(13, 6),)
    assert generated(c, ctx) == () and not any(
        t["transformation_target_id"].startswith("asset:")
        for t in plan(c, ctx).transformations
    )


def test_forged_or_missing_prepared_label_correction_is_rejected():
    c = case("641932")
    specs = list(generated(c))
    specs[0] = {**specs[0], "sha256": "0" * 64}
    with pytest.raises(UnsupportedCondition):
        plan(c, assets=tuple(specs))
    with pytest.raises(UnsupportedCondition):
        plan(c, assets=())


def test_common_base_figure_in_an_unreviewed_stage_is_rejected():
    c = case("630105")
    s = BeautifulSoup(parent(c), "html.parser")
    im = s.img.extract()
    s.select("[data-inline-latex]")[0].insert_after(im)
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=str(s))


def test_parent_integer_declaration_after_a_stray_dot_keeps_all_signed_families():
    from solution_runner.pipelines.equations.exam_trigonometric_parameters import (
        affine_families,
    )

    c = case("500447")
    source = affine_families(parent(c))
    assert source == ((R(1, 2), 1, "k"), (-R(1, 6), 2, "k"), (-R(5, 6), 2, "k"))
    a = analysis(c)
    assert a.series == ((R(1, 2), 1), (-R(1, 6), 2), (-R(5, 6), 2))
    p = plan(c)
    f = formulas(p.solution_html)
    assert any(r"- \frac{\pi}{6}" in x for x in f) and any(
        r"- \frac{5 \pi}{6}" in x for x in f
    )
    assert p.answer.index(r"- \frac{\pi}{6}") < p.answer.index(r"- \frac{5 \pi}{6}")
    assert not any(r"\frac{7 \pi}{6}" in x or r"\frac{11 \pi}{6}+2" in x for x in f)
