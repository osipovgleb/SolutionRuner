"""Preserve a sine auxiliary angle and both affine zero-factor families."""

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
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_sum_identities import (
    compile_identity,
    style,
)
from solution_runner.pipelines.equations.exam_trigonometric_sum_product import X
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_auxiliary_sine.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    _, f, interval, bounds = read(c["context"])
    return analyze(formula or f, interval, bounds, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_conditions_and_circles(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        assert not t["transformation_target_id"].startswith("asset:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_roots_and_original_interval_follow_independent_equation(c):
    a = analysis(c)
    full = tuple(map(R, ("1/6", "5/18", "17/18", "29/18")))
    assert a.sum_product.kind == "auxiliary_sine" and a.scale == R(1, 2)
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == tuple(map(R, ("-11/6", "-31/18", "-19/18")))
    assert a.series == ((R(5, 18), R(2, 3)), (R(1, 6), 2))
    assert [(b.variable, b.angle_scale, b.angle_shift) for b in a.branches] == [
        (C, 3, R(1, 12)),
        (S, 1, -R(1, 12)),
    ]
    with mp.workdps(65):
        for n in range(-432, 433):
            q = R(n, 108)
            x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
            value = 2 * mp.sin(2 * x) - mp.cos(x) - mp.sqrt(3) * mp.sin(x)
            assert (abs(value) < mp.mpf("1e-50")) == (q % 2 in full)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_source_circle_matches_all_four_roots_and_exact_selected_labels(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    assert len(e["green_markers"]) == 4 and not e.get("corrected_file")
    for p in e["green_markers"]:
        f = p["native_frame"]
        assert p["path_d"] in paths and f["path_d"] in paths
        theta = float(decode(p["angle"]) * sp.pi)
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(theta),
                p["y"] - f["cy"] + f["ry"] * math.sin(theta),
            )
            < 1
        )
    validate(e, analysis(c))
    changed = deepcopy(e)
    changed["bounds"][0] = "-3"
    with pytest.raises(UnsupportedCondition):
        validate(changed, analysis(c))


def test_proof_keeps_sine_auxiliary_identity_and_cosine_branch_first():
    html = plan(CASES[0]).solution_html
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert "формулы синуса суммы" in html and "формулу разности синусов" in html
    assert "формулы косинуса суммы" not in html
    cosine = next(
        i for i, f in enumerate(forms) if f.startswith(r"\cos") and f.endswith("=0")
    )
    sine = next(
        i
        for i, f in enumerate(forms)
        if f.startswith(r"\sin") and f.count(r"\sin") == 1 and f.endswith("=0")
    )
    assert cosine < sine
    assert r"\frac{5 \pi}{18}" in html and r"\frac{\pi}{6}" in html


@pytest.mark.parametrize("multiple", [2, 3, 4, 5, 7, 11])
def test_same_certificate_supports_bounded_higher_sines_without_group_dispatch(
    multiple,
):
    formula = rf"2\sin {multiple}x-\cos x=\sqrt{{3}}\sin x"
    a = analysis(CASES[0], formula)
    expected = (
        (R(1, 6) / (multiple - 1), R(2, multiple - 1)),
        (R(5, 6) / (multiple + 1), R(2, multiple + 1)),
    )
    assert (
        select(a.series, (-4, 4, True, True))[0]
        == select(expected, (-4, 4, True, True))[0]
    )
    product = a.sum_product.normalizer * a.sum_product.product
    evaluate = sp.lambdify(X, product, "mpmath")
    with mp.workdps(65):
        for n in range(-14, 15):
            x = mp.mpf(n) / 7
            original = 2 * mp.sin(multiple * x) - mp.cos(x) - mp.sqrt(3) * mp.sin(x)
            assert abs(original - evaluate(x)) < mp.mpf("1e-50")


@pytest.mark.parametrize(
    "coefficient,expected_phase", [(r"\sqrt{3}", R(1, 6)), (r"-\sqrt{3}", R(5, 6))]
)
def test_signs_change_the_auxiliary_phase_instead_of_changing_the_source_method(
    coefficient, expected_phase
):
    eq = compile_identity(
        r"2\sin 2x-\cos x=" + coefficient + r"\sin x", "auxiliary_sine"
    )
    shifted = eq.sum_product.identities[0][1]
    assert shifted == sp.sin(X + expected_phase * sp.pi, evaluate=False)


@pytest.mark.parametrize(
    "formula",
    [
        r"2\sin 2x-\cos x=\sin x",
        r"2\cos 2x-\cos x=\sqrt{3}\sin x",
        r"2\sin 13x-\cos x=\sqrt{3}\sin x",
        r"2\sin 2x-\cos x+1=\sqrt{3}\sin x",
        r"2\sin 2x+\sin 3x-\cos x=\sqrt{3}\sin x",
        r"\frac{2\sin 2x-\cos x}{\sin x}=\sqrt{3}",
        r"2\sin 2x-\frac{3}{5}\sin x=\frac{4}{5}\cos x",
        r"5\sin 2x-3\sin x=4\cos x",
    ],
)
def test_unequal_amplitudes_foreign_angles_original_poles_and_unknown_phases_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_identity(formula, "auxiliary_sine")


def test_unknown_original_circle_is_rejected_without_fallback_picture():
    ctx = deepcopy(CASES[0]["context"])
    asset = ctx["normalized_content"]["assets"][0]
    asset["asset_id"] = "unknown-circle"
    asset["url"] = "/assets/unknown-circle"
    with pytest.raises(UnsupportedCondition):
        plan(CASES[0], ctx)


def test_parent_method_requires_mathematical_steps_and_not_only_a_prose_keyword():
    assert style(parent(CASES[0])) == "auxiliary_sine"
    assert (
        style("<p>Преобразуем разность синусов с помощью вспомогательного угла.</p>")
        is None
    )
    ctx = deepcopy(CASES[0]["context"])
    prototype = parent(CASES[0]) + "<p>Ещё одно решение.</p>"
    with pytest.raises(UnsupportedCondition):
        get_handler(get_group_profile("627924").content_rule_key).plan(
            PlanInput(ctx, parent_solution_html=prototype)
        )


@pytest.mark.parametrize("closed", [True, False])
def test_exact_source_root_at_interval_endpoint_respects_bracket(closed):
    a = analysis(CASES[0])
    roots = select(a.series, (-R(11, 6), -R(31, 18), True, closed))[0]
    assert roots == ((-R(11, 6), -R(31, 18)) if closed else (-R(11, 6),))
