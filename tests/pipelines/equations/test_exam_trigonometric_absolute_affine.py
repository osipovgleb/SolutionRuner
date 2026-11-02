"""One absolute value retains sign restrictions, parent cases and native figures."""

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
    operands,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_absolute_affine.json"
    ).read_text()
)["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent(c))


def plan(c, ctx=None, html=None):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert handler.diagram_specs(ctx or c["context"]) == ()
    return handler.plan(
        PlanInput(
            ctx or c["context"],
            parent_solution_html=parent(c) if html is None else html,
        )
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equations_independently_verify_complete_and_selected_roots(c):
    a = analysis(c)
    expected = (
        ((R(0), R(5, 4)), (R(77, 4), R(20)))
        if c["task"] == "559902"
        else ((R(1), R(5, 4)), (R(1), R(5, 4)))
    )
    assert (a.residues, a.selected) == expected
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues, *a.selected]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            value = (
                mp.sqrt(2) * mp.cos(x + mp.pi / 4) - s - abs(t)
                if c["task"] == "559902"
                else abs(t - 2 * s) + t
            )
            assert (abs(value) < mp.mpf("1e-50")) == (q % 2 in a.residues)
    assert all(a.bounds[0] <= q <= a.bounds[1] for q in a.selected)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_condition_and_assets(
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
        item = next((v for v in items if v["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_sign_method_and_source_figure_stage_are_preserved(c):
    a = analysis(c)
    html = plan(c).solution_html
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert html.count('data-asset-id="' + aid + '"') == 1
    if c["task"] == "559902":
        assert a.absolute_affine.split_sign and a.image_position == "absolute-case"
        assert a.series == ((R(0), R(2)), (R(-3, 4), R(2)))
        assert (
            html.index('data-inline-latex="(\\cos x)&lt;0"')
            < html.index(aid)
            < html.index("косинуса суммы")
        )
        assert any(b.angle_shift == R(1, 4) for b in a.branches)
        assert r"- \frac{3 \pi}{4}" in html
    else:
        assert not a.absolute_affine.split_sign and a.image_position == "outside"
        assert a.series == ((R(1), R(2)), (R(5, 4), R(2)))
        assert html.index(aid) < html.index("Модуль неотрицателен")
        assert "системе" in html and r"-(\cosx)\ge0" in html.replace(" ", "")
    assert "возвед" not in html


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_svg_bytes_paths_points_and_fixed_reference_frame(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert len(e["green_markers"]) == 2 and not e["excluded_markers"]
    for p in e["green_markers"]:
        assert p["path_d"] in paths
        f = p["native_frame"]
        assert f["path_d"] in paths
        q = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(q),
                p["y"] - f["cy"] + f["ry"] * math.sin(q),
            )
            < 1
        )
    validate(e, analysis(c))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_circle_and_changed_interval_are_rejected(c):
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
    "formula", [r"|\cos x|=-\cos x", r"|\cos x|=\cos x", r"|\sin x|=\sin x"]
)
def test_continua_are_not_misrepresented_as_finite_root_families(formula):
    with pytest.raises(UnsupportedCondition):
        operands(formula)


@pytest.mark.parametrize(
    "formula",
    [r"|\cos x-2\sin x|+\cos x+1=0", r"|\cos x|=1", r"|\sin x-2\cos x|-\cos x=0"],
)
def test_parent_sign_constraint_and_complete_equation_are_not_guessed_from_roots(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_absolute(formula, parent(CASES[1]))


@pytest.mark.parametrize(
    "formula",
    [
        r"|\sin^2x|=\cos x",
        r"\sin x|\cos x|=1",
        r"|\sin x+\frac{\cos x}{\cos x}|=0",
        r"|\sin y|=\cos y",
        r"|\cos x|+r=0",
        r"|\sin\alpha|=\cos\alpha",
    ],
)
def test_nonlinear_absolute_coefficients_original_poles_and_other_variables_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        operands(formula)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_additional_methods_or_roots_alone_do_not_replace_parent_computation(c):
    _, f, _, _ = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        compile_absolute(f, "<p>Другое решение</p>" + parent(c))
    with pytest.raises(UnsupportedCondition):
        compile_absolute(f, r'<p><span data-inline-latex="x=\pi+2\pi k"></span></p>')


def test_intermediate_case_image_cannot_be_moved_before_the_sign_constraint():
    c = CASES[0]
    soup = BeautifulSoup(parent(c), "html.parser")
    img = soup.find("img")
    img.extract()
    soup.insert(0, img)
    with pytest.raises(UnsupportedCondition):
        plan(c, html=str(soup))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_catalog_bindings_reuse_existing_runner_with_exact_metadata(c):
    p = get_group_profile(c["group"])
    expected = (
        (
            "ded15ef6-60e7-4916-8b71-da81cdfea2e0",
            "81adff3f-4a92-408f-abf4-4881018613e5",
            18,
        )
        if c["task"] == "559902"
        else (
            "77704472-7441-4618-9349-c206c377efe2",
            "76619b09-5e8b-45b2-baad-ae54e9eaf162",
            42,
        )
    )
    assert (p.source_group_id, p.snapshot_theme_id, p.group_order_index) == expected
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


def test_fresh_affine_absolute_expression_reuses_global_sign_method():
    c = CASES[1]
    a = analysis(c, r"|\cos x-\frac{2}{\sqrt{3}}\sin x|+\cos x=0")
    assert a.residues == (R(1), R(4, 3))
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            value = abs(mp.cos(x) - 2 / mp.sqrt(3) * mp.sin(x)) + mp.cos(x)
            assert (abs(value) < mp.mpf("1e-50")) == (q % 2 in a.residues)


def test_zero_absolute_boundary_belongs_to_closed_case_only():
    from solution_runner.pipelines.equations.exam_trigonometric_absolute_affine import (
        cases,
    )

    html = r'<p><span data-inline-latex="|\sin x|=0"></span><span data-inline-latex="\sin x\ge0"></span><span data-inline-latex="\sin x\lt0"></span></p>'
    compiled = compile_absolute(r"|\sin x|=0", html)
    rows = cases(compiled.absolute_affine)
    assert {q for b in rows[0][-1] for q in b.residues} == {R(0), R(1)}
    assert not {q for b in rows[1][-1] for q in b.residues}


def test_source_inverse_phase_cannot_move_to_the_other_sign_case():
    with pytest.raises(UnsupportedCondition):
        analysis(CASES[0], r"|\cos x|=-\cos x+2\sin x")
