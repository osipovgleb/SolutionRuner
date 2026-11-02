"""Whole two-base factorizations retain both branches and audited source circles."""

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
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_grouping import (
    X,
    Y,
    compile_grouping,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.probability.common import line
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_power_grouping.json"
    ).read_text()
)["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None, html=None):
    _, f, interval, bounds = read(c["context"])
    return analyze(formula or f, interval, bounds, parent(c) if html is None else html)


def plan(c, context=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert h.diagram_specs(context or c["context"]) == ()
    return h.plan(PlanInput(context or c["context"], parent_solution_html=parent(c)))


def neighbor(p, q, k, sign=1, function="cos", scale=3):
    argument = rf"\{function} {scale}x"
    t = ("-" if sign < 0 else "") + argument
    exponent = str(2 * sign) + argument
    formula = rf"{p**3 * q}^{{{t}}}+{k}\cdot {p**3}^{{{t}}}={p}^{{{5 * sign}{argument}}}+{k}\cdot {p * q}^{{{t}}}"
    first, second = rf"{p}^{{{exponent}}}={k}", rf"{q}^{{{t}}}={p}^{{{exponent}}}"
    html = (
        line(formula)
        + line(rf"({p}^{{{exponent}}}-{k})({q}^{{{t}}}-{p}^{{{exponent}}})=0")
        + line(first)
        + line(second)
    )
    return formula, html


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equation_independently_certifies_all_and_selected_roots(c):
    a = analysis(c)
    assert a.scale == 3
    assert a.series == ((R(1, 6), R(1, 3)),)
    assert a.selected == (R(-3, 2), R(-7, 6), R(-5, 6))
    data = a.power_equality.grouping
    assert data.bases == (5, 6)
    assert data.positive_factor == X
    assert data.polynomial == sp.expand((X**2 - 30) * (X**2 - Y))
    with mp.workdps(65):
        for n in range(-216, 217):
            q = R(n, 48)
            t = mp.cos(3 * mp.pi * n / 48)
            value = (
                mp.power(750, t)
                + 6 * mp.power(125, mp.mpf(1) / 3 + t)
                - mp.power(5, 5 * t)
                - mp.power(30, 1 + t)
            )
            root = abs(value) < mp.mpf("1e-50")
            assert root == ((q - R(1, 6)) / R(1, 3)).is_Integer
            assert (q in a.selected) == (root and R(-7, 4) <= q <= R(-3, 4))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_replay_preserves_original_sources(c):
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
        item = next(v for v in items if v["transformation_target_id"] == key)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_substitution_order_and_intermediate_figure_are_preserved(c):
    a = analysis(c)
    data = a.power_equality.grouping
    soup = BeautifulSoup(parent(c), "html.parser")
    image = str(soup.find("img"))
    html = render(a, image)[2]
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert r"\begin{cases}" not in " ".join(forms)
    assert data.ratio == R(6, 25)
    assert any(r"\frac{6}{25}" in f and "=1" in f for f in forms)
    assert "хотя бы один" in html
    assert "положительный множитель" in html
    assert "формулу двойного угла" not in html
    assert html.count("data-asset-id=") == 1
    if c["task"] == "649745":
        assert data.substitution == "t"
        assert data.order == (data.univariate, data.mixed)
        assert a.image_position == "after-polynomial"
        assert html.index(image) < html.index("не имеет решений")
        assert forms.index(r"t=\frac{1}{2}\log_{5}30") < forms.index("t=0")
    else:
        assert data.substitution is None
        assert data.order == (data.mixed, data.univariate)
        assert a.image_position == "outside"
        assert html.startswith(image)
        assert forms.index(data.argument_text + "=0") < forms.index(
            data.argument_text + r"=\log_{25}30"
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_circle_hash_six_roots_and_three_labels(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    validate(entry, analysis(c))
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    assert set(entry["residues"]) == {"1/6", "1/2", "5/6", "7/6", "3/2", "11/6"}
    assert entry["labels"] == ["-3/2", "-7/6", "-5/6"]
    assert len(entry["green_markers"]) == 6
    for marker in entry["green_markers"]:
        frame = marker["native_frame"]
        assert marker["path_d"] in paths and frame["path_d"] in paths
        angle = float(R(marker["angle"])) * math.pi
        error = math.hypot(
            marker["x"] - frame["cx"] - frame["rx"] * math.cos(angle),
            marker["y"] - frame["cy"] + frame["ry"] * math.sin(angle),
        )
        assert error < (0.668 if c["task"] == "649745" else 3.784)


@pytest.mark.parametrize("p,q,k", [(7, 10, 52), (3, 14, 11), (2, 15, 5), (2, 3, 9)])
@pytest.mark.parametrize("sign", [1, -1])
def test_bases_are_derived_for_neighbors_reciprocals_and_split_rational_factors(
    p, q, k, sign
):
    formula, html = neighbor(p, q, k, sign)
    compiled = compile_grouping(formula, html)
    assert compiled.raw == C and compiled.scale == 3
    data = compiled.power_equality.grouping
    assert set(data.bases) == {sp.Integer(p) ** sign, sp.Integer(q) ** sign}
    assert data.level == k
    assert data.ratio not in (0, 1)


@pytest.mark.parametrize("k", [1, 24, 25])
def test_a_possible_extra_branch_is_never_discarded(k):
    formula, html = neighbor(5, 6, k)
    with pytest.raises(UnsupportedCondition):
        compile_grouping(formula, html)


@pytest.mark.parametrize("function,scale", [("sin", 1), ("cos", 2), ("sin", 3)])
def test_neighbor_arguments_reuse_the_existing_trigonometric_solver(function, scale):
    formula, html = neighbor(5, 6, 30, function=function, scale=scale)
    html += (
        line(rf"\{function} {scale}x=0") + "<p>Отберём корни с помощью неравенств.</p>"
    )
    a = analyze(formula, r"[-2\pi;0]", (-2 * sp.pi, R(0), True, True), html)
    assert a.scale == scale
    assert a.preferred == (S if function == "sin" else C)
    expected = tuple(
        q
        for q in (R(n, 2 * scale) for n in range(-4 * scale, 1))
        if ((2 * scale * q).is_even if function == "sin" else (2 * scale * q).is_odd)
    )
    assert a.selected == expected


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("replacement", ["7\\cdot", "6\\cdot 124", "+1="])
def test_changed_whole_source_cannot_reuse_parent_factorization(c, replacement):
    _, formula, _, _ = read(c["context"])
    if replacement == "+1=":
        formula = formula.replace("=", "+1=", 1)
    elif replacement == "6\\cdot 124":
        formula = formula.replace("125", "124", 1)
    else:
        formula = formula.replace(r"6\cdot", replacement, 1)
    with pytest.raises(UnsupportedCondition):
        analysis(c, formula=formula)


@pytest.mark.parametrize(
    "change",
    ["wrong-substitution", "missing-substitution", "wrong-factor", "extra-method"],
)
def test_unknown_or_changed_parent_method_is_rejected(change):
    c = CASES[0]
    html = parent(c)
    if change == "wrong-substitution":
        html = html.replace(r"t=\cos 3x", r"t=\cos 2x", 1)
    elif change == "missing-substitution":
        html = html.replace(r"t=\cos 3x", "0=0", 1)
    elif change == "wrong-factor":
        html = html.replace("5^{2t}-30", "5^{2t}-31")
    else:
        html += "<p>Ещё одно решение</p>"
    with pytest.raises(UnsupportedCondition):
        analysis(c, html=html)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_figure_or_interval_is_rejected(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    a = analysis(c)
    from dataclasses import replace

    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    with pytest.raises(UnsupportedCondition):
        validate(CIRCLES[aid], replace(a, bounds=(R(-2), R(-1), True, True)))


@pytest.mark.parametrize("c,index", list(zip(CASES, (34, 38))))
def test_catalog_reuses_existing_handler(c, index):
    profile = get_group_profile(c["group"])
    assert profile.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert profile.snapshot_theme_id == "76619b09-5e8b-45b2-baad-ae54e9eaf162"
    assert profile.group_order_index == index
