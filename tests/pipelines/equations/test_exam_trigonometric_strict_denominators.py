"""Original strict domains, physical double angles and four native source figures."""

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
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_proof import first, formula
from solution_runner.pipelines.equations.exam_trigonometric_strict_quotient import (
    compile_quotient,
    source_branches,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_strict_denominators.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "673034": ((R(1, 3), R(3, 2), R(5, 3)), (R(7, 2), R(11, 3), R(13, 3))),
    "695392": ((R(7, 6),), (-R(17, 6), -R(5, 6))),
    "699433": ((R(7, 6), R(11, 6)), (R(19, 6),)),
    "699852": ((R(7, 12), R(13, 12)), (-R(35, 12),)),
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


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        s, c = mp.sin(x), mp.cos(x)
        eps = mp.mpf("1e-48")
        if key == "673034":
            n = 1 + mp.sin(2025 * mp.pi / 2 - 2 * x) + mp.cos(2025 * mp.pi - x)
            r = 2025 - 2025 * s
        elif key == "695392":
            if abs(c) < eps:
                return False
            n = 2 * s * s * c + mp.sqrt(3) * s * s - 2 * c - mp.sqrt(3)
            r = mp.tan(x)
        elif key == "699433":
            if abs(c) < eps:
                return False
            n = 2 * s * s - s - 1
            r = -c * mp.tan(x)
        else:
            n = 2 * c * c - mp.sqrt(3) * mp.sin(2 * x) - 1
            r = -c
        return r > eps and abs(n / mp.sqrt(r)) < mp.mpf("1e-43")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_roots_satisfy_original_unreduced_equation_and_strict_domains(c):
    a = analysis(c)
    full, selected = EXPECTED[c["task"]]
    assert a.scale == 1 and a.strict_domain is True
    assert select(a.series, (0, 2, True, False))[0] == full and a.selected == selected
    for q in (*full, *selected):
        assert original_zero(c["task"], q)
    for q in (R(n, 96) for n in range(192)):
        assert original_zero(c["task"], q) == (q in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_catalogue_registration_reuses_shared_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_answers_are_unused_and_local_replay_preserves_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
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
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


def test_affine_radicand_retains_only_one_parity_of_zero_cosine():
    a = analysis(case("673034"))
    assert a.domain == 2025 * (1 - S) and not a.poles
    assert set(source_branches(a, False)[0].residues) == {
        R(1, 3),
        R(1, 2),
        R(3, 2),
        R(5, 3),
    }
    assert R(3, 2) in a.residues and R(1, 2) not in a.residues
    assert (-R(1, 2), 2) in a.series
    html = plan(case("673034")).solution_html
    assert "Знаменатель равен нулю" in html and r"\sin x\ne1" in formulas(html)


def test_grouping_divides_only_after_original_pole_and_preserves_progressions():
    a = analysis(case("695392"))
    assert (
        a.poles == (C,) and a.domain == S * C and a.selection_method == "progressions"
    )
    assert a.series == ((-R(5, 6), 2),)
    candidates = source_branches(a, False)
    assert len(candidates) == 1 and 0 not in candidates[0].candidates
    html = plan(case("695392")).solution_html
    f = formulas(html)
    assert f.index(formula(C) + r"\ne0") < f.index(formula(C * C) + ">0")
    assert formula((2 * C + sp.sqrt(3)) * (S * S - 1)) + "=0" in f
    assert formula(-C * C * (2 * C + sp.sqrt(3))) + "=0" in f
    assert not any(s == formula(C) + "=0" for s in f)
    assert "Длина промежутка" in html


def test_cancellation_keeps_original_tangent_pole_and_domain_figure_stage():
    a = analysis(case("699433"))
    assert a.strict_quotient.radicand == -S and a.poles == (C,)
    assert not original_zero("699433", R(3, 2))
    soup = BeautifulSoup(plan(case("699433")).solution_html, "html.parser")
    first_part = soup.find("li")
    text = str(first_part)
    assert text.index("-1&lt;\\sin x&lt;0") < text.index("<img") < text.index("D=")
    assert a.image_position == "after-intro"


def test_double_angle_keeps_physical_partial_orbit_and_parent_order():
    c = case("699852")
    a = analysis(c)
    unfiltered = source_branches(a, False)
    assert len(a.branches) == 1 and a.branches[0].angle_scale == 2
    assert unfiltered[0].residues == (R(1, 12), R(7, 12), R(13, 12), R(19, 12))
    assert a.series == ((R(7, 12), 2), (R(13, 12), 2))
    intro, steps = first(a)
    assert r"2\cos^{2}x-1=\cos2x" in formulas(intro)
    f = formulas(steps)
    tangent = next(i for i, s in enumerate(f) if r"\tg 2x" in s)
    domain = f.index(r"-\cos x>0")
    assert tangent < domain and r"\cos2x\ne0" in f
    html = plan(c).solution_html
    assert html.index("=\\cos2x") < html.index("<img") < html.index("деление")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_sources_match_geometry_domains_and_unchanged_bytes(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    nodes = list(ET.fromstring(raw).iter())
    paths = {n.get("d"): n for n in nodes if n.tag.endswith("path")}
    for p in (
        *entry["green_markers"],
        *entry["boundary_markers"],
        *entry["excluded_markers"],
    ):
        assert paths[p["path_d"]].get("fill") == p["fill"]
        frame = entry["native_frames"][p["native_frame"]]
        assert frame["path_d"] in paths
        q = float(sp.sympify(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - frame["cx"] - frame["rx"] * math.cos(q),
                p["y"] - frame["cy"] + frame["ry"] * math.sin(q),
            )
            < 0.4
        )
        if p in entry["excluded_markers"]:
            assert len(p["cross_segments"]) == 2
            for segment in p["cross_segments"]:
                assert segment["element"] in [
                    dict(n.attrib) for n in nodes if n.tag.endswith("line")
                ]
    validate(entry, analysis(c))
    html = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert len(html.find_all("img")) == 1 and html.img["data-asset-id"] == aid


def test_shading_and_open_axes_retain_strict_product_domain():
    c = case("695392")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    assert (
        entry["selection_kind"] == "all_roots" and entry["figure_role"] == "derivation"
    )
    assert {sp.sympify(p["angle"]) for p in entry["open_domain_markers"]} == {
        0,
        R(1, 2),
        1,
        R(3, 2),
    }
    assert len(entry["excluded_markers"]) == 3
    paths = {
        n.get("d"): n
        for n in ET.fromstring(
            gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        ).iter()
        if n.tag.endswith("path")
    }
    for p in entry["open_domain_markers"]:
        assert (
            paths[p["path_d"]].get("fill") == "#FFFFFF"
            and paths[p["path_d"]].get("stroke") == "#FC0606"
        )
    for p in entry["strict_product_shading"]["paths"]:
        assert paths[p["path_d"]].get("opacity") == "0.3"
        x0, x1, y0, y1 = p["bbox"]
        f = entry["circle"]
        assert (
            (x0 >= f[0] - 0.1 and y0 >= f[1] - 0.1)
            if p["invalid_quadrant"] == 4
            else (x1 <= f[0] + 0.1 and y1 <= f[1] + 0.1)
        )
    changed = deepcopy(entry)
    changed["strict_product_shading"]["invalid_quadrants"] = [1, 3]
    with pytest.raises(UnsupportedCondition, match="shaded quadrants"):
        validate(changed, analysis(c))


@pytest.mark.parametrize("key", EXPECTED)
def test_missing_or_unknown_source_cannot_silently_drop_reviewed_figure(key):
    c = case(key)
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"] = []
    section(ctx["normalized_content"], "solution")["asset_keys"] = []
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize(
    "radicand", [r"\cos x+\sin x", r"\sin^2 x", r"\tg2x", r"1+\tg x"]
)
def test_new_radicand_shapes_fail_closed(radicand):
    with pytest.raises(UnsupportedCondition):
        compile_quotient(
            r"\frac{2\cos^2 x-\cos x}{\sqrt{" + radicand + r"}}=0",
            parent(case("673034")),
        )


def test_changed_domain_and_selection_certificates_fail_closed():
    c = case("695392")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = deepcopy(CIRCLES[aid])
    entry["strict_quotient_domain"]["poles"] = []
    with pytest.raises(UnsupportedCondition, match="strict denominator domain"):
        validate(entry, analysis(c))
    entry = deepcopy(CIRCLES[aid])
    entry["residues"] = ["5/6"]
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))


def test_additional_method_and_named_substitution_are_not_silently_ignored():
    _, f, _, _ = read(case("673034")["context"])
    for extra in (
        "<p>Другое решение</p>",
        r'<p><span data-inline-latex="t=\cos x"></span></p>',
    ):
        with pytest.raises(UnsupportedCondition):
            compile_quotient(f, parent(case("673034")) + extra)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_cannot_drop_its_audited_figure_stage(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    soup.img.decompose()
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=str(soup))


@pytest.mark.parametrize("key", ["699433", "699852"])
def test_parent_cannot_move_an_inside_figure_outside_its_part(key):
    c = case(key)
    soup = BeautifulSoup(parent(c), "html.parser")
    image = soup.img.extract()
    soup.insert(0, image)
    with pytest.raises(UnsupportedCondition, match="strict denominator domain"):
        plan(c, prototype=str(soup))
