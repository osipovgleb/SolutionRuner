"""Keep zero common factors and the complete domain of a logarithm denominator."""

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
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_absolute_affine import (
    compile_absolute,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_power_polynomial import (
    polynomial_source,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_absolute_product_and_power_log.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent(c))


def plan(c, ctx=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert h.diagram_specs(ctx or c["context"]) == ()
    return h.plan(PlanInput(ctx or c["context"], parent_solution_html=parent(c)))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equation_and_original_domain_independently_verify_every_root(c):
    a = analysis(c)
    full = (
        tuple(map(R, ["1/4", "1/3", "2/3", "3/4", "5/4", "4/3", "5/3", "7/4"]))
        if c["task"] == "548032"
        else (R(5, 6),)
    )
    selected = (
        tuple(map(R, ["-3/4", "-2/3", "-1/3", "-1/4", "1/4", "1/3"]))
        if c["task"] == "548032"
        else (R(5, 6),)
    )
    assert (a.residues, a.selected) == (full, selected)
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *full, *selected]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            if c["task"] == "548032":
                value = abs(t + mp.cos(3 * x)) + mp.cos(2 * x)
            else:
                arg = 1 - 3 * t
                if arg <= 0 or abs(arg - 1) < mp.mpf("1e-55"):
                    assert q % 2 not in full
                    continue
                value = (
                    mp.power(16, s) - 3 * mp.power(4, mp.mpf("0.5") + s) + 8
                ) / mp.log(arg, 2)
            assert (abs(value) < mp.mpf("1e-50")) == (q % 2 in full)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_condition_and_original_assets(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((x for x in items if x["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before


def test_product_proof_keeps_zero_common_factor_and_three_parent_series():
    c = case("548032")
    a = analysis(c)
    html = plan(c).solution_html
    assert a.scale == 1 and a.absolute_affine.common == (r"\cos2x", sp.S.One)
    assert a.series == ((R(1, 4), R(1, 2)), (R(-1, 3), R(1)), (R(1, 3), R(1)))
    assert {R(1, 4), R(3, 4), R(5, 4), R(7, 4)} <= set(a.residues)
    assert "На общий множитель не делим" in html
    assert html.index(r"\cos2x=0") < html.index(r"(\cos x)=- \frac{1}{2}")
    assert r"\cos2x\le0" in html
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert html.index(aid) < html.index("Раскроем модуль")


def test_log_proof_retains_argument_positive_nonunit_and_whole_denominator_nonzero():
    c = case("561193")
    a = analysis(c)
    html = plan(c).solution_html
    assert a.power_polynomial.log_denominator[0] == 2
    assert a.strict_domain and not a.power_polynomial.strict_root
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    wrapper = a.power_polynomial.wrapper
    assert wrapper + r"\ne0" in forms and wrapper + ">0" not in forms
    assert r"(\cos x)<\frac{1}{3}" in forms and r"(\cos x)\ne0" in forms
    assert any(f.endswith(r"\ne1") for f in forms)
    assert "может быть отрицательным" in html and "числитель равен нулю" in html
    assert "Подкоренное выражение" not in html
    assert "нарушает исходную область определения" in html


@pytest.mark.parametrize("coefficient", [r"\sqrt{2}", "2", "3"])
def test_fresh_common_factor_coefficients_keep_all_zero_factor_roots_without_duplicates(
    coefficient,
):
    a = analysis(case("548032"), r"|\cos x+\cos3x|=-" + coefficient + r"\cos2x")
    assert a.residues == tuple(map(R, ["1/4", "3/4", "5/4", "7/4"]))
    assert a.selected == (R(-3, 4), R(-1, 4), R(1, 4))
    with mp.workdps(65):
        weight = mp.sqrt(2) if coefficient == r"\sqrt{2}" else int(coefficient)
        for n in range(-216, 217):
            q = R(n, 48)
            x = mp.pi * n / 48
            v = abs(mp.cos(x) + mp.cos(3 * x)) + weight * mp.cos(2 * x)
            assert (abs(v) < mp.mpf("1e-50")) == (q % 2 in a.residues)


@pytest.mark.parametrize(
    "numerator,wrapper,kind,full",
    [
        (
            r"16^{\sin x}-3\cdot4^{\sin x}+2",
            r"\log_2(1-\frac12\cos x)",
            "affine",
            ["0", "1/6", "5/6", "1"],
        ),
        (
            r"16^{\sin x}-3\cdot4^{\sin x}+2",
            r"\log_{\frac12}(1-\frac12\cos x)",
            "half-base",
            ["0", "1/6", "5/6", "1"],
        ),
        (
            r"16^{\sin x}-6\cdot4^{\sin x}+8",
            r"\log_2(\frac{1+\cos x}{2})",
            "half-arg",
            ["1/6", "1/2", "5/6"],
        ),
        (
            r"16^{\sin x}-3\cdot4^{\sin x}+2",
            r"\log_2(\frac{1-\cos x}{\sin x})",
            "rational",
            ["1/6", "5/6"],
        ),
        (
            r"16^{\sin x}-3\cdot4^{\sin x}+2",
            r"\log_2(1-\cos x)",
            "zero-arg",
            ["1/6", "5/6", "1"],
        ),
    ],
)
def test_negative_logarithms_and_original_argument_poles_use_the_actual_domain(
    numerator, wrapper, kind, full
):
    wrapper = wrapper.replace(r"\frac12", r"\frac{1}{2}")
    a = analysis(case("561193"), r"\frac{" + numerator + "}{" + wrapper + "}=0")
    assert a.residues == tuple(map(R, full))
    with mp.workdps(65):
        for n in range(-216, 217):
            q = R(n, 48)
            x = mp.pi * n / 48
            s, t = mp.sin(x), mp.cos(x)
            if kind == "rational" and abs(s) < mp.mpf("1e-55"):
                assert q % 2 not in a.residues
                continue
            arg = (
                (1 + t) / 2
                if kind == "half-arg"
                else (1 - t) / s
                if kind == "rational"
                else 1 - t
                if kind == "zero-arg"
                else 1 - t / 2
            )
            if arg <= mp.mpf("1e-55") or abs(arg - 1) < mp.mpf("1e-55"):
                assert q % 2 not in a.residues
                continue
            num = (
                mp.power(16, s)
                - (6 if kind == "half-arg" else 3) * mp.power(4, s)
                + (8 if kind == "half-arg" else 2)
            )
            denominator = mp.log(arg, mp.mpf(1) / 2 if kind == "half-base" else 2)
            assert (abs(num / denominator) < mp.mpf("1e-50")) == (q % 2 in a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_svg_native_geometry_and_red_crosses_are_preserved(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert len(e["green_markers"]) == (8 if c["task"] == "548032" else 1)
    assert len(e["excluded_markers"]) == (0 if c["task"] == "548032" else 2)
    for p in (*e["green_markers"], *e["excluded_markers"]):
        f = p["native_frame"]
        assert f["path_d"] in paths and p["path_d"] in paths
        q = float(R(p["angle"])) * math.pi
        assert math.hypot(
            p["x"] - f["cx"] - f["rx"] * math.cos(q),
            p["y"] - f["cy"] + f["ry"] * math.sin(q),
        ) < (5 if c["task"] == "548032" else 2)
        for cross in p.get("cross_segments", []):
            assert any(
                n.tag.endswith(cross["tag"]) and dict(n.attrib) == cross["attributes"]
                for n in root.iter()
            )
    validate(e, analysis(c))


def test_original_log_domain_boundary_lines_and_shading_are_bound_to_actual_argument():
    c = case("561193")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    root = ET.fromstring(gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()))
    assert len(e["native_log_boundaries"]) == 2
    for boundary in e["native_log_boundaries"]:
        assert boundary["error_px"] < 1
        assert any(
            n.tag.endswith("line") and dict(n.attrib) == boundary["attributes"]
            for n in root.iter()
        )
    assert any(
        n.tag.endswith("path") and n.get("fill") == e["native_log_shade_fill"]
        for n in root.iter()
    )
    ctx = deepcopy(c["context"])
    condition = section(ctx["normalized_content"], "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    node = soup.select_one("[data-inline-latex]")
    node["data-inline-latex"] = node["data-inline-latex"].replace("1-3", "1-4")
    condition["html"] = str(soup)
    a = analysis(c, node["data-inline-latex"])
    assert a.residues == analysis(c).residues
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_or_changed_interval_cannot_reuse_original_figure(c):
    ctx = deepcopy(c["context"])
    asset = ctx["normalized_content"]["assets"][0]
    asset["asset_id"] = "unknown"
    asset["url"] = "/assets/unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = deepcopy(CIRCLES[aid])
    e["bounds"][0] = "-100"
    with pytest.raises(UnsupportedCondition):
        validate(e, analysis(c))


@pytest.mark.parametrize(
    "wrapper",
    [
        r"\log_2^2(1-3\cos x)",
        r"\log_2(1-3\cos x)+1",
        r"\log_2(1-3\cos x)\cos x",
        r"\log_2(1-3\cos x)\log_3(1-3\cos x)",
        r"\log_{\cos x}(1-3\cos x)",
        r"\log_1(1-3\cos x)",
        r"\log_{-2}(1-3\cos x)",
        r"\log_2(\sin^2x+\cos^2x)",
        r"\log_2(\sin^2x+\cos^2x-1)",
    ],
)
def test_nonwhole_logs_invalid_bases_and_identically_undefined_denominators_fail_closed(
    wrapper,
):
    f = r"\frac{16^{\sin x}-3\cdot4^{\frac12+\sin x}+8}{" + wrapper + "}=0"
    with pytest.raises(UnsupportedCondition):
        polynomial_source(f.replace(r"\frac12", r"\frac{1}{2}"))


@pytest.mark.parametrize(
    "formula",
    [
        r"|\cos^4x|=-\cos2x",
        r"|\cos^3x|=-\cos2x",
        r"|\cos x(\sin^2x+\cos^2x-1)|=-(\sin^2x+\cos^2x-1)",
    ],
)
def test_unreviewed_polynomial_ratios_and_continuous_identities_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_absolute(formula, parent(case("548032")))


@pytest.mark.parametrize(
    "html",
    [
        r'<span data-inline-latex="\cos2x\le0"></span><span data-inline-latex="\cos x+\cos3x=-\cos2x"></span>',
        r'<span data-inline-latex="\cos2x\le0"></span><span data-inline-latex="x=\frac{\pi}{4}+\frac{\pi k}{2}"></span>',
        r'<span data-inline-latex="\cos2x\ge0"></span><span data-inline-latex="\cos x+\cos3x=-\cos2x"></span><span data-inline-latex="\cos x+\cos3x=\cos2x"></span>',
    ],
)
def test_both_parent_product_branches_and_correct_sign_are_required(html):
    with pytest.raises(UnsupportedCondition):
        compile_absolute(r"|\cos x+\cos3x|=-\cos2x", html)


@pytest.mark.parametrize("binding", DATA["bindings"], ids=lambda x: x["group"])
def test_exact_catalog_bindings_share_existing_handler(binding):
    p = get_group_profile(binding["group"])
    assert (p.source_group_id, p.snapshot_theme_id, p.group_order_index) == (
        binding["uuid"],
        binding["theme"],
        binding["index"],
    )
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
