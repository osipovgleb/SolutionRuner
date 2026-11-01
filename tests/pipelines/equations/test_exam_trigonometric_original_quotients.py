"""Original poles, parent cancellation order and the valid unselected open root."""

import gzip
import hashlib
import json
import math
import re
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
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_original_quotients import (
    compile_quotient,
    source_branches,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import first, formula
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_original_quotients.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "629862": ((R(2, 3), R(4, 3)), (R(22, 3), R(26, 3))),
    "635306": (
        (R(1, 6), R(1, 2), R(5, 6), R(7, 6), R(3, 2), R(11, 6)),
        (-R(5, 6), -R(1, 2), -R(1, 6), R(1, 6), R(1, 2)),
    ),
    "645888": ((R(5, 4), R(7, 4)), (-R(11, 4), -R(9, 4))),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, ctx=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            ctx or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        s, c = mp.sin(x), mp.cos(x)
        eps = mp.mpf("1e-48")
        if key == "629862":
            if abs(mp.cos(mp.pi - x)) < eps or abs(mp.sin(2 * x)) < eps:
                return False
            lhs = mp.sin(3 * mp.pi - x) - mp.tan(mp.pi - x)
            rhs = (1 - mp.sin(7 * mp.pi / 2 + x) ** 2) / mp.sin(2 * x)
        elif key == "635306":
            if abs(mp.cos(2 * x)) < eps or abs(s) < eps:
                return False
            lhs = mp.tan(2 * x)
            rhs = 2 * mp.cos(2 * x) * c / s
        else:
            if abs(c) < eps or abs(s) < eps:
                return False
            lhs = mp.sin(2 * x) / mp.tan(x)
            rhs = (
                mp.sqrt(2) * mp.sin(x / 2) ** 4 - mp.sqrt(2) * mp.cos(x / 2) ** 4
            ) / mp.tan(x)
        return abs(lhs - rhs) < mp.mpf("1e-43")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_follow_unreduced_original_equations(c):
    a = analysis(c)
    full, selected = EXPECTED[c["task"]]
    assert (
        a.scale == 1
        and select(a.series, (0, 2, True, False))[0] == full
        and a.selected == selected
    )
    for q in (*full, *selected):
        assert original_zero(c["task"], q)
    for q in (R(n, 96) for n in range(192)):
        assert original_zero(c["task"], q) == (q in full)
    for q in (R(n, 4) for n in range(8)):
        if any(
            sp.simplify(p.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})) == 0
            for p in a.poles
        ):
            assert not original_zero(c["task"], q)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalogue_binding_uses_existing_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_all_source_inputs(c):
    original = deepcopy(c["context"])
    ctx = deepcopy(original)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        assert t["transformation_target_id"].startswith("section:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == original
    assert (
        p.condition_html == section(original["normalized_content"], "condition")["html"]
    )
    assert (
        ctx["normalized_content"]["assets"] == original["normalized_content"]["assets"]
    )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


def test_cancelling_original_sine_does_not_publish_an_extra_zero_sine_case():
    a = analysis(case("629862"))
    d = a.original_quotient
    assert a.poles == (-C, 2 * S * C) and d.divide == S and d.right == S / (2 * C)
    assert len(a.branches) == 1 and a.branches[0].variable == C
    f = forms(plan(case("629862")).solution_html)
    assert formula(S) + r"\ne0" in f and not any(s == formula(S) + "=0" for s in f)
    assert f.index(formula(S) + r"\ne0") < f.index(formula(d.polynomial) + "=0")
    assert not any("t=" in s for s in f)


def test_fourth_power_difference_precedes_original_nonzero_cosine_division():
    c = case("645888")
    a = analysis(c)
    d = a.original_quotient
    assert d.half[2] == sp.sqrt(2) and d.divide == C and a.poles == (C, S)
    assert d.left == 2 * S * C and d.right == -sp.sqrt(2) * C
    f = forms(plan(c).solution_html)
    factor = next(
        i for i, s in enumerate(f) if r"\right)\left(" in s and r"\sin^{2}" in s
    )
    linear = f.index(formula(d.polynomial) + "=0")
    assert factor < linear and f.index(formula(C) + r"\ne0") < factor
    assert formula(C) + "=0" not in f
    assert not any(s.startswith("t=") for s in f)


def test_double_angle_cosine_zero_is_retained_and_three_parent_families_stay_separate():
    a = analysis(case("635306"))
    d = a.original_quotient
    assert a.poles == (2 * C * C - 1, S) and C not in a.poles
    assert d.divide == 1 and len(source_branches(d, False)) == 3
    assert a.series == ((R(1, 2), 1), (R(1, 6), 1), (-R(1, 6), 1))
    assert all(original_zero("635306", q) for q in (R(1, 2), R(3, 2)))
    html = plan(case("635306")).solution_html
    f = forms(html)
    first_factor = next(i for i, s in enumerate(f) if r"\cos x\left(\cos2x-" in s)
    quadratic = next(i for i, s in enumerate(f) if s.startswith("D="))
    assert first_factor < quadratic and formula(C) + "=0" in f
    assert "уже входят в ветвь нулевого косинуса" in html


def resolved_nodes(raw):
    root = ET.fromstring(raw)
    css = " ".join(n.text or "" for n in root.iter() if n.tag.endswith("style"))
    rules = {
        name: dict(p.split(":", 1) for p in body.split(";") if ":" in p)
        for name, body in re.findall(r"\.([\w-]+)\s*\{([^}]+)\}", css)
    }
    result = []
    for n in root.iter():
        props = {}
        for name in n.get("class", "").split():
            props.update(rules.get(name, {}))
        props.update(n.attrib)
        result.append((n, props))
    return result


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_svg_bytes_styles_and_all_native_markers_match_math(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    nodes = resolved_nodes(raw)
    paths = {n.get("d"): (n, props) for n, props in nodes if n.tag.endswith("path")}
    points = (
        *e["green_markers"],
        *e["boundary_markers"],
        *e.get("unselected_root_markers", []),
    )
    for p in points:
        assert any(
            n.get("d") == p["path_d"] and props.get("fill") == p["fill"]
            for n, props in nodes
        )
        frame = e["native_frames"][p["native_frame"]]
        assert frame["path_d"] in paths
        q = float(sp.sympify(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - frame["cx"] - frame["rx"] * math.cos(q),
                p["y"] - frame["cy"] + frame["ry"] * math.sin(q),
            )
            < 1
        )
    assert not e["excluded_markers"]
    validate(e, analysis(c))
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert len(soup.find_all("img")) == 1 and soup.img["data-asset-id"] == aid
    if c["task"] == "629862":
        assert soup.img.find_parent("li") is None
    else:
        first_part = soup.find("li")
        assert first_part.img is soup.img
        assert str(first_part).index("<img") < str(first_part).index("До сокращения")


def test_open_green_point_is_a_valid_unselected_root_and_retains_fill_and_outline():
    c = case("635306")
    a = analysis(c)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    assert e["point_scope"] == "selected" and len(e["green_markers"]) == 5
    assert e["complete_residues"] == list(map(str, EXPECTED["635306"][0]))
    (point,) = e["unselected_root_markers"]
    q = sp.sympify(point["angle"])
    assert q == R(5, 6) and q in a.residues and q not in {v % 2 for v in a.selected}
    assert original_zero("635306", q) and point["fill"] == "#FFFFFF"
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    nodes = resolved_nodes(raw)
    assert point["element"] in [dict(n.attrib) for n, _ in nodes]
    assert point["outline_element"] in [dict(n.attrib) for n, _ in nodes]
    changed = deepcopy(e)
    changed["unselected_root_markers"][0]["angle"] = "1/6"
    with pytest.raises(UnsupportedCondition, match="valid root outside selection"):
        validate(changed, a)
    changed = deepcopy(e)
    changed["unselected_root_markers"][0]["angle"] = "0"
    with pytest.raises(UnsupportedCondition):
        validate(changed, a)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_missing_source_or_changed_bounds_cannot_reuse_figure(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"] = []
    section(ctx["normalized_content"], "solution")["asset_keys"] = []
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    e = deepcopy(CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]])
    e["bounds"][0] = "999"
    with pytest.raises(UnsupportedCondition):
        validate(e, analysis(c))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_cannot_drop_or_move_audited_figure(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    img = soup.img.extract()
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=str(soup))
    if c["task"] != "629862":
        soup.insert(0, img)
        with pytest.raises(
            UnsupportedCondition, match="original quotient poles and method"
        ):
            plan(c, prototype=str(soup))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_pole_certificate_cannot_change(c):
    e = deepcopy(CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]])
    e["original_quotient_domain"]["poles"] = []
    with pytest.raises(
        UnsupportedCondition, match="original quotient poles and method"
    ):
        validate(e, analysis(c))


@pytest.mark.parametrize("key", EXPECTED)
def test_additional_substitution_and_method_are_not_silently_ignored(key):
    c = case(key)
    _, f, _, _ = read(c["context"])
    for extra in (
        r'<p><span data-inline-latex="t=\sin x"></span></p>',
        "<p>Другое решение</p>",
    ):
        with pytest.raises(UnsupportedCondition):
            compile_quotient(f, parent(c) + extra)


@pytest.mark.parametrize(
    "key,old,new,expected",
    [
        ("629862", r"\frac{1-\sin^2", r"\frac{3-3\sin^2", (R(1, 3), R(5, 3))),
        ("645888", r"\sqrt{2}", "1", (R(7, 6), R(11, 6))),
        ("635306", r"\tg 2x", r"\tg(2x+\pi)", EXPECTED["635306"][0]),
    ],
)
def test_coefficients_and_periodic_angles_are_computed_from_the_condition(
    key, old, new, expected
):
    c = case(key)
    _, f, i, b = read(c["context"])
    changed = f.replace(old, new)
    assert changed != f
    a = analyze(changed, i, b, parent(c))
    assert select(a.series, (0, 2, True, False))[0] == expected
    first(a)


@pytest.mark.parametrize(
    "key,formula",
    [
        ("629862", r"\sin x-\tg x=\frac{1}{\sin 2x}"),
        ("635306", r"\tg 2x=-2\cos2x\ctg x"),
        ("635306", r"\tg 3x=2\cos2x\ctg x"),
        (
            "645888",
            r"\frac{\sin2x}{\tg x}=\frac{\sin^4\frac{x}{2}+\cos^4\frac{x}{2}}{\tg x}",
        ),
        (
            "645888",
            r"\frac{\sin2x}{\tg x}=\frac{\sin^4\frac{x}{2}-\cos^4\frac{x}{2}}{\ctg x}",
        ),
    ],
)
def test_new_shapes_and_unjustified_cancellations_fail_closed(key, formula):
    with pytest.raises(UnsupportedCondition):
        compile_quotient(formula, parent(case(key)))
