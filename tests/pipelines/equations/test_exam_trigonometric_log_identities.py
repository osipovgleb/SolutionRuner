"""Original log domains, reciprocal substitutions and three preserved native SVGs."""

import gzip
import hashlib
import json
import math
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
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_identities.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "634660": ((R(1, 4),), (R(17, 4),)),
    "636515": ((R(1, 3),), (R(19, 3),)),
    "696418": ((R(1, 4), R(7, 4)), (-R(15, 4),)),
    "704819": ((R(1, 6), R(5, 6)), (-R(11, 6), -R(7, 6))),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c):
    _, f, i, b = read(c["context"])
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
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        s, c = mp.sin(x), mp.cos(x)
        eps = mp.mpf("1e-50")
        if key == "636515":
            if s <= eps or abs(s - 1) < eps or abs(c) < eps:
                return False
            lhs = 1 / c**2 + 1 / mp.sin(x - mp.pi / 2)
            rhs = mp.log(s * s) / mp.log(s)
        elif key == "696418":
            if c <= eps or abs(c - 1) < eps or s * s <= eps:
                return False
            lhs = mp.log(c, 2) * mp.log(s * s) / mp.log(c)
            rhs = -1
        elif key == "704819":
            b = mp.cos(2 * x)
            if s <= eps or b <= eps or abs(s - 1) < eps or abs(b - 1) < eps:
                return False
            lhs = mp.log(b) / mp.log(s) + mp.log(s) / mp.log(b)
            rhs = 2
        else:
            b = mp.sin(2 * x) / 2
            if s <= eps or c <= eps or b <= eps or abs(b - 1) < eps:
                return False
            lhs = mp.log(s) / mp.log(b) * mp.log(c) / mp.log(b)
            rhs = mp.mpf(1) / 4
        return abs(lhs - rhs) < mp.mpf("1e-45")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_follow_the_original_equation_and_every_log_domain(c):
    a = analysis(c)
    full, chosen = EXPECTED[c["task"]]
    assert (
        a.scale == 1
        and select(a.series, (0, 2, True, False))[0] == full
        and a.selected == chosen
    )
    for q in (*full, *chosen):
        assert original_zero(c["task"], q) and failed(a, q) is None
    for q in (R(n, 96) for n in range(192)):
        assert original_zero(c["task"], q) == (q in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalogue_registration_reuses_the_shared_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_local_replay_preserves_original_inputs(c):
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


def test_power_identity_keeps_both_original_reciprocal_poles_and_no_named_substitution():
    c = case("636515")
    a = analysis(c)
    assert a.poles == (C * C, -C)
    assert (S, "positive") in conditions(a) and (S - 1, "nonzero") in conditions(a)
    f = formulas(plan(c).solution_html)
    assert not any(s.startswith("t=") for s in f)
    first = next(i for i, s in enumerate(f) if s == r"\frac{1}{(\cos x)}=-1")
    second = next(i for i, s in enumerate(f) if s == r"\frac{1}{(\cos x)}=2")
    assert first < second
    assert failed(a, R(1, 2)) is not None and failed(a, R(3, 2)) is not None


def test_chain_cancellation_does_not_restore_the_forbidden_base_one():
    a = analysis(case("696418"))
    assert (C - 1, "nonzero") in conditions(a)
    assert failed(a, sp.S.Zero) == (C - 1, "nonzero", 0)
    html = plan(case("696418")).solution_html
    f = formulas(html)
    assert r"\log_a b\cdot\log_b c=\log_a c" in f
    assert a.series == ((-R(1, 4), sp.Integer(2)), (R(1, 4), sp.Integer(2)))


def test_common_product_base_keeps_the_parent_rational_substitution_and_open_endpoint():
    c = case("634660")
    a = analysis(c)
    f = formulas(plan(c).solution_html)
    assert a.bounds == (R(9, 4), R(9, 2), False, True) and R(9, 4) not in a.selected
    assert a.log_product.equality.identity.substitution == "t"
    assert any(r"\frac{t}{(1+t)^2}" in s for s in f)
    assert "t>0" in f and r"t\ne-1" in f
    assert not any(r"\quadt" in s for s in f)
    assert any(r"\tg x=1" == s for s in f)


def test_reciprocal_log_circle_stays_between_log_quadratic_and_back_substitution():
    c = case("704819")
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    im = soup.img
    assert im.find_parent("li").get("data-list-marker") == "а)"
    assert (
        im.find_previous("span", attrs={"data-inline-latex": True})["data-inline-latex"]
        == "t=1"
    )
    assert im.find_next("span", attrs={"data-inline-latex": True})[
        "data-inline-latex"
    ].startswith(r"\log_")
    a = analysis(c)
    assert (2 * C * C - 2, "nonzero") in conditions(a)


def test_two_outside_chain_circles_keep_domain_before_a_and_selection_before_b():
    c = case("696418")
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    images = soup.find_all("img")
    assert len(images) == 2 and images[0].find_parent("li") is None
    assert images[1].find_parent("li").get("data-list-marker") == "а)"
    assert images[1].find_next("li").get("data-list-marker") == "б)"
    assets = c["context"]["normalized_content"]["assets"]
    first, second = (CIRCLES[a["asset_id"]] for a in assets)
    assert (
        first["selection_kind"] == "all_roots"
        and first["selection_companion"] == assets[1]["asset_id"]
    )
    assert len(second["green_markers"]) == 2 and second["labels"] == ["-15/4"]


@pytest.mark.parametrize(
    "identifier",
    [
        "30085433-3461-4e4e-bda1-973516a4674c",
        "493bf8da-0dbf-4c2e-b8dc-ffd006880ac8",
        "6a390f6f-1221-4602-90b8-3dbf3aad41f4",
    ],
)
def test_native_source_markers_keep_exact_bytes_and_their_own_quarter_frames(
    identifier,
):
    e = CIRCLES[identifier]
    svg = gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == e["sha256"]
    root = ET.fromstring(svg)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    for p in (*e["green_markers"], *e["boundary_markers"], *e["excluded_markers"]):
        frame = e["native_frames"][p["native_frame"]]
        q = float(R(p["angle"])) * math.pi
        assert p["path_d"] in paths and frame["path_d"] in paths
        assert (
            math.hypot(
                p["x"] - frame["cx"] - frame["rx"] * math.cos(q),
                p["y"] - frame["cy"] + frame["ry"] * math.sin(q),
            )
            < 0.2
        )
    assert not e.get("corrected_file")


def test_open_base_boundaries_shaded_domain_and_both_native_crosses_are_preserved():
    identifier = "30085433-3461-4e4e-bda1-973516a4674c"
    e = CIRCLES[identifier]
    root = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    assert len(e["open_domain_markers"]) == 3 and len(e["excluded_markers"]) == 2
    assert {R(p["angle"]) for p in e["open_domain_markers"]} == {0, R(1, 2), R(3, 2)}
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert e["invalid_cosine_halfplane"]["path_d"] in paths
    for p in e["open_domain_markers"]:
        assert p["path_d"] in paths and p["distance"] < 0.2
    lines = [dict(n.attrib) for n in root.iter() if n.tag.endswith("line")]
    for p in e["excluded_markers"]:
        assert len(p["cross_segments"]) == 2
        for cross in p["cross_segments"]:
            assert cross["element"] in lines


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_extra_parent_methods_and_unknown_condition_instructions_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c) + "<p>Другое решение.</p>")
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    s["html"] = s["html"].replace("Ре\xadши\xadте", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
