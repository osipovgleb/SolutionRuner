"""Original poles are checked before inverse angles and after partial root branches."""

import gzip
import hashlib
import json
import math
import re
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
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
    solve_branches,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S, T
from solution_runner.pipelines.equations.exam_trigonometric_domain import (
    forbidden_level,
    without_poles,
)
from solution_runner.pipelines.equations.exam_trigonometric_positive_factors import (
    compile_mixed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_remaining_poles.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ORIGINAL = {
    "622096": (
        2 * (C + sp.sqrt(3)) / (C / S),
        sp.sqrt(3) * S / C,
        (S, C),
        1,
        (R(5, 6), R(7, 6)),
        (R(-5, 6),),
    ),
    "622377": (
        (C - 1) / C + 2 * (C / S) * S,
        0,
        (S, C),
        1,
        (R(1, 3), R(5, 3)),
        (R(-7, 3), R(-5, 3)),
    ),
    "622981": (
        (2 * (S / C) ** 2 + 5 * S / C) / (2 * S * C + 5 * C * C),
        0,
        (C, 2 * S * C + 5 * C * C),
        1,
        (sp.S.Zero, sp.S.One),
        (sp.S.One, sp.Integer(2)),
    ),
    "623657": (
        (S / C) / (1 + C),
        C - 1,
        (C, 1 + C),
        3,
        (sp.S.Zero, R(2, 3), R(4, 3)),
        (sp.S.Zero, R(2, 3)),
    ),
    "624294": (
        (1 + 2 * S * S - 3 * sp.sqrt(2) * S + 2 * S * C) / (2 * S * C - 1),
        1,
        (2 * S * C - 1,),
        1,
        (R(3, 4),),
        (R(-13, 4), R(-5, 4)),
    ),
    "628749": (
        (3 * (1 - 2 * S * S) + 7 * S - 5) / (9 * C * C - 5),
        0,
        (9 * C * C - 5,),
        1,
        (R(1, 6), R(5, 6)),
        (R(-11, 6),),
    ),
    "628775": (
        (5 * (1 - 2 * S * S) + 9 * S - 7) / (25 * C * C - 21),
        0,
        (25 * C * C - 21,),
        1,
        (R(1, 6), R(5, 6)),
        (R(-23, 6),),
    ),
}


def case(key):
    return next(e for e in CASES if e["task"] == key)


def parent(e):
    p = case(e["group"])
    return section(p["context"]["normalized_content"], "solution")["html"]


def analysis(e, context=None):
    _, formula, interval, bounds = read(context or e["context"])
    return analyze(formula, interval, bounds, parent(e))


def plan(e, context=None):
    return get_handler(get_group_profile(e["group"]).content_rule_key).plan(
        PlanInput(context or e["context"], parent_solution_html=parent(e))
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_reuses_the_common_runner(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_complete_and_selected_roots_follow_the_original_equation(e):
    a = analysis(e)
    left, right, poles, scale, full, selected = ORIGINAL[e["task"]]
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == full
    assert a.selected == selected and a.scale == scale
    expression = sp.sympify(left) - right
    for q in (*full, *selected):
        sub = {S: sp.sin(scale * q * sp.pi), C: sp.cos(scale * q * sp.pi)}
        assert all(sp.simplify(p.subs(sub)) != 0 for p in poles)
        assert sp.simplify(expression.subs(sub)) == 0
    value = sp.lambdify((S, C), expression, "math")
    pole_values = [sp.lambdify((S, C), p, "math") for p in poles]
    window = select(a.series, (-4, 4, True, True))[0]
    for k in range(-96, 97):
        q = R(k, 24)
        si, co = (
            math.sin(float(scale * q) * math.pi),
            math.cos(float(scale * q) * math.pi),
        )
        actual = all(abs(p(si, co)) > 1e-9 for p in pole_values)
        actual = actual and abs(value(si, co)) < 1e-9
        assert (q in window) == actual, (e["task"], q)


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_saved_answers_are_unused_and_replay_preserves_condition_and_sources(e):
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
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert e["context"] == before
    assert (
        get_handler(get_group_profile(e["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )
    assert (
        BeautifulSoup(p.solution_html, "html.parser").find("img")["src"]
        == before["normalized_content"]["assets"][0]["url"]
    )


def test_parent_division_by_nonzero_tangent_is_not_replaced_by_a_zero_sine_case():
    e = case("622096")
    a = analysis(e)
    html = plan(e).solution_html
    assert a.ratio_division == (T, 2 * C + 2 * sp.sqrt(3), sp.sqrt(3))
    assert len(a.branches) == 1 and a.branches[0].variable == C
    assert "разделить на него" in html
    nodes = formulas(html)
    assert r"\frac{1}{(\ctg x)}=(\tg x)" in nodes
    assert not any(f.startswith(r"(\sin x)=0") for f in nodes)


def test_zero_sine_pole_stays_forbidden_when_cosine_is_minus_one():
    a = analysis(case("622377"))
    assert set(a.poles) == {S, C}
    assert sp.S.One not in a.residues
    assert "Нулевая величина в знаменателе" in plan(case("622377")).solution_html


def test_original_tangent_numerator_is_factored_before_any_cancellation():
    e = case("622981")
    html = plan(e).solution_html
    assert "исходный числитель" in html and r"\left(2 (\tg x) + 5\right)" in html
    assert r"(\tg x)=- \frac{5}{2}\quad\Longrightarrow\quad" in html
    assert "D=" not in html and r"(\cos x)^{3}" not in html
    assert analysis(e).branches[0].excluded == (-R(5, 2),)


def test_scaled_mixed_factor_keeps_the_parent_double_angle_impossibility_method():
    e = case("623657")
    a = analysis(e)
    html = plan(e).solution_html
    assert set(a.poles) == {C, C + 1} and a.series == ((sp.S.Zero, R(2, 3)),)
    assert a.positive_factorization[-1] == "mixed_double"
    nodes = formulas(html)
    assert r"\sin(6 x)=-2" in nodes
    assert nodes.index(r"(\tg 3 x)=(\cos 3 x)^{2} - 1") < nodes.index(r"\sin(6 x)=-2")
    assert "Модуль синуса не превосходит 1" in html
    assert any(r"\frac{\pi}{3}" in f and r"\frac{2 \pi k}{3}" in f for f in nodes)


def test_partial_sine_level_shows_the_forbidden_series_and_the_surviving_series():
    html = plan(case("624294")).solution_html
    nodes = formulas(html)
    assert any(r"\frac{\pi}{4}" in f and "x=" in f for f in nodes)
    assert any(r"\frac{3 \pi}{4}" in f and "x=" in f for f in nodes)
    assert r"\sin(2 x)\ne 1" in nodes
    assert r"x\ne \frac{\pi}{4}+\pi n,\quad n\in\mathbb Z" in nodes
    assert "Эта серия обращает исходный знаменатель в нуль" in html
    assert "После проверки исходных ограничений остаются серии" in html
    assert "отрезок от −1 до 1" in html


@pytest.mark.parametrize(
    "key,level,denominator",
    [("628749", R(2, 3), 9 * C * C - 5), ("628775", R(2, 5), 25 * C * C - 21)],
)
def test_nontable_function_levels_are_removed_by_original_poles_before_angles(
    key, level, denominator
):
    a = analysis(case(key))
    b = a.branches[0]
    assert level in b.candidates and level in b.excluded and level not in b.values
    assert forbidden_level(S, level, (denominator,))
    assert without_poles((b,), a.poles)[0].excluded == b.excluded
    html = plan(case(key)).solution_html
    assert "исключаем до вычисления углов" in html
    assert not any(name in html for name in (r"\arcsin", r"\arccos", r"\arctan"))


def test_a_pole_at_only_one_sign_of_the_other_function_does_not_remove_the_level():
    value = R(2, 3)
    one = C + sp.sqrt(5) / 3
    assert not forbidden_level(S, value, (one,))
    assert forbidden_level(S, value, (one, C - sp.sqrt(5) / 3))
    assert forbidden_level(S, sp.S.One, (C,))
    assert not forbidden_level(S, sp.S.One, (C + 1,))
    with pytest.raises(UnsupportedCondition):
        solve_branches(S - value, S, poles=(one,))
    _, branches = solve_branches(
        (S - value) * (S - sp.S.Half), S, poles=(9 * C * C - 5,)
    )
    assert branches[0].values == (sp.S.Half,) and branches[0].excluded == (value,)


@pytest.mark.parametrize("factor", [1 + 2 * S * C, 1 + 3 * S * C])
def test_mixed_factor_at_or_inside_sine_range_is_not_declared_impossible(factor):
    with pytest.raises(UnsupportedCondition):
        compile_mixed(S * factor, C * (C + 1), (C, C + 1), ())


def test_an_unrecorded_denominator_factor_cannot_be_cleared():
    with pytest.raises(UnsupportedCondition):
        compile_mixed(S * (1 + S * C), C * (C + 2), (C, C + 1), ())


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_native_svg_points_exact_bytes_and_full_root_certificates(e):
    a = analysis(e)
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    validate(entry, a)
    svg = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    root = ET.fromstring(svg)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    cx, cy, _ = entry["circle"]
    full = ORIGINAL[e["task"]][4]
    for p in entry["green_markers"]:
        assert p["path_d"] in paths and p["native_circle_path"] in paths
        q = R(p["angle"])
        assert q in full
        angle = float(q) * math.pi
        assert (
            math.hypot(
                p["x"] - cx - p["radius"] * math.cos(angle),
                p["y"] - cy + p["radius"] * math.sin(angle),
            )
            < 5
        )
    if entry.get("point_scope") == "selected":
        assert tuple(map(R, entry["complete_residues"])) == a.residues


def test_outer_marker_uses_its_own_native_curve_ray_intersection():
    e = case("624294")
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    p = next(p for p in entry["green_markers"] if "native_ray_intersection" in p)
    cert = p["native_ray_intersection"]
    assert cert["native_path"] == p["native_circle_path"]
    assert cert["angle"] == p["angle"] == "3/4"
    assert cert["native_center"] == entry["circle"][:2]
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)", cert["native_path"])
    assert tokens.pop(0) == "M"
    current = complex(float(tokens.pop(0)), float(tokens.pop(0)))
    segments = []
    while tokens:
        assert tokens.pop(0) == "c"
        points = [complex(float(tokens.pop(0)), float(tokens.pop(0))) for _ in range(3)]
        segments.append((current, *(current + v for v in points)))
        current += points[-1]
    center = complex(*cert["native_center"])
    direction = complex(-1, -1)

    def point(segment, t):
        a, b, c, d = segment
        return (
            (1 - t) ** 3 * a
            + 3 * (1 - t) ** 2 * t * b
            + 3 * (1 - t) * t * t * c
            + t**3 * d
        )

    def cross(z):
        z -= center
        return z.real * direction.imag - z.imag * direction.real

    matches = []
    for seg in segments:
        lo, hi = 0.0, 1.0
        if cross(point(seg, lo)) * cross(point(seg, hi)) > 0:
            continue
        for _ in range(60):
            mid = (lo + hi) / 2
            if cross(point(seg, lo)) * cross(point(seg, mid)) <= 0:
                hi = mid
            else:
                lo = mid
        matches.append(point(seg, (lo + hi) / 2))
    assert len(matches) == 1
    target = matches[0]
    assert abs(target - complex(*cert["point"])) < 1e-7
    assert abs(abs(target - center) - p["radius"]) < 1e-7
    assert abs(target - complex(p["x"], p["y"])) < 5
    assert math.isclose(cert["error"], 1.308493963804285, abs_tol=1e-7)


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_unknown_source_and_changed_interval_do_not_reuse_audited_labels(e):
    ctx = deepcopy(e["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(e, ctx)
    a = analysis(e)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(
            entry, replace(a, bounds=(sp.Integer(-10), sp.Integer(10), True, True))
        )


def test_existing_public_angle_helpers_remain_available_after_branch_extraction():
    from solution_runner.pipelines.equations import exam_trigonometric as main
    from solution_runner.pipelines.equations.exam_trigonometric_compile import table
    from solution_runner.pipelines.equations.exam_trigonometric_inverse import angles

    assert main.table is table and main.angles is angles
