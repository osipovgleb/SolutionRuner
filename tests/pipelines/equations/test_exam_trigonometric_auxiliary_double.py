"""Keep the reviewed auxiliary double angle and filter the original physical roots."""

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
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.exam_trigonometric_radical_equation import (
    compile_radical,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_style import kind
from solution_runner.pipelines.equations.exam_trigonometric_safe_square import (
    auxiliary_series,
    double_polynomial,
)
from solution_runner.pipelines.equations.exam_trigonometric_safe_square_proof import (
    checked_values,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_auxiliary_double.json"
    ).read_text()
)
CASES = DATA["cases"]
CASE = CASES[0]
CTX = CASE["context"]
PARENT = section(CTX["normalized_content"], "solution")["html"]
AID = CTX["normalized_content"]["assets"][0]["asset_id"]
HANDLER = get_handler(get_group_profile(CASE["group"]).content_rule_key)
R = sp.Rational


def analysis(formula=None, parent=PARENT):
    _, original, interval, bounds = read(CTX)
    return analyze(formula or original, interval, bounds, parent)


def plan(context=None):
    return HANDLER.plan(PlanInput(context or CTX, parent_solution_html=PARENT))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_condition_and_circle(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    actual = plan(ctx)
    assert actual == plan()
    for t in actual.transformations:
        assert not t["transformation_target_id"].startswith(
            ("section:condition", "asset:")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(ctx).transformations == ()
    assert (
        actual.condition_html
        == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before
    assert HANDLER.diagram_specs(before) == ()


def test_complete_and_selected_roots_follow_the_original_equation_independently():
    a = analysis()
    assert a.residues == (sp.S.Zero, R(7, 4))
    assert a.series == ((sp.S.Zero, 2), (-R(1, 4), 2))
    assert a.selected == (-R(9, 4), -sp.Integer(2), -R(1, 4), sp.S.Zero)
    with mp.workdps(65):
        for n in range(-216, 217):
            q = R(n, 48)
            x = mp.mpf(n) * mp.pi / 48
            rad = 4 * mp.cos(2 * x) - 2 * mp.sin(2 * x)
            if abs(rad) < mp.mpf("1e-55"):
                rad = mp.mpf(0)
            expected = rad >= 0 and abs(mp.sqrt(rad) - 2 * mp.cos(x)) < mp.mpf("1e-50")
            assert expected == (q % 2 in a.residues)
    assert select(a.series, (-R(5, 2), 0, True, False))[0] == a.selected[:-1]


def test_auxiliary_phase_and_nominal_parities_are_in_the_original_variable():
    a = analysis()
    b = a.radical_equation.auxiliary_branch
    assert kind(PARENT) == "safe_square"
    assert not a.radical_equation.mixed_factors
    assert b.variable == C and b.angle_scale == 2 and b.angle_shift == R(1, 4)
    assert b.residues == (0, R(3, 4), 1, R(7, 4))
    assert auxiliary_series(b) == ((0, 1), (-R(1, 4), 1))
    assert a.branches[0].residues == (0, R(7, 4))
    assert checked_values(a, 0)[-1] and checked_values(a, -R(1, 4))[-1]
    assert checked_values(a, 1)[1] == -2 and not checked_values(a, 1)[-1]
    assert (
        checked_values(a, R(3, 4))[1] == -sp.sqrt(2)
        and not checked_values(a, R(3, 4))[-1]
    )
    assert a.raw == a.radical_equation.squared


def test_proof_keeps_double_angle_lowering_normalization_and_original_sign_checks():
    p = plan()
    soup = BeautifulSoup(p.solution_html, "html.parser")
    forms = [
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    ]
    assert r"\cos^2x=\frac{1+\cos2x}{2}" in forms
    shifted = next(
        i for i, f in enumerate(forms) if r"\cos" in f and r"2x+\frac{\pi}{4}" in f
    )
    assert r"\cos\left(2x+\frac{\pi}{4}\right)" in forms[shifted]
    assert any(f.startswith(r"2x+\frac{\pi}{4}=") for f in forms)
    parity = next(i for i, f in enumerate(forms) if f.startswith("k=2n"))
    assert forms.index(r"\cos^2x=\frac{1+\cos2x}{2}") < shifted < parity
    assert any("k=2n+1" in f and r"\text{праваячасть}=-2" in f for f in forms)
    assert (
        soup.get_text(" ", strip=True).count("Серия удовлетворяет исходному уравнению")
        == 2
    )
    assert "Произведение равно нулю" not in soup.get_text(" ", strip=True)
    images = soup.find_all("img")
    assert len(images) == 1 and images[0]["data-asset-id"] == AID
    assert images[0].find_parent("li") is None


def test_native_circle_keeps_multiple_visits_on_the_two_original_frames():
    e = CIRCLES[AID]
    raw = gzip.decompress((DIRECTORY / (AID + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert sorted(p["angle"] for p in e["green_markers"]) == ["0", "7/4", "7/4"]
    assert e["labels"] == ["-9/4", "-2", "-1/4", "0"]
    assert len({p["radius"] for p in e["green_markers"]}) == 2
    for p in e["green_markers"]:
        frame = p["native_frame"]
        assert p["path_d"] in paths and frame["path_d"] in paths
        q = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - frame["cx"] - frame["rx"] * math.cos(q),
                p["y"] - frame["cy"] + frame["ry"] * math.sin(q),
            )
            < 1
        )
    validate(e, analysis())


@pytest.mark.parametrize(
    "formula,full",
    [
        (r"\sqrt{16\cos 2x-8\sin 2x}=4\cos x", (0, R(7, 4))),
        (r"2\sqrt{4\cos 2x-2\sin 2x}=4\cos x", (0, R(7, 4))),
        (r"-\sqrt{4\cos 2x-2\sin 2x}=-2\cos x", (0, R(7, 4))),
        (r"\sqrt{4\cos 2x-2\sin 2x}=-2\cos x", (R(3, 4), 1)),
        (r"\frac{\sqrt{4\cos 2x-2\sin 2x}\sin x}{\sin x}=2\cos x", (R(7, 4),)),
    ],
)
def test_scaled_weight_opposite_sign_and_original_cancelled_pole_use_the_same_method(
    formula, full
):
    a = analysis(formula)
    assert a.residues == full
    assert a.radical_equation.auxiliary_branch is not None
    html = render(a, "")[2]
    assert html.count("чётном и нечётном") == 1
    if a.radical_equation.multiplier != 1:
        assert "ненулевую постоянную перед корнем" in html
    if r"\frac" in formula:
        assert a.poles == (S,)
        assert r"\text{исходный знаменатель}=0" in html


def test_sine_auxiliary_presentation_reuses_the_same_phase_certificate():
    parent = PARENT.replace(r"\cos (2x+\frac{\pi}{4})", r"\sin (2x+\frac{3\pi}{4})")
    assert parent != PARENT
    a = analysis(parent=parent)
    b = a.radical_equation.auxiliary_branch
    assert b.variable == S and b.angle_shift == R(3, 4)
    assert a.residues == (0, R(7, 4))
    assert "синуса суммы" in render(a, "")[2]


@pytest.mark.parametrize("phase", [r"\frac{\pi}{6}", r"\frac{\pi}{3}"])
def test_a_parent_phase_that_does_not_certify_the_original_polynomial_is_rejected(
    phase,
):
    parent = PARENT.replace(r"\cos (2x+\frac{\pi}{4})", r"\cos (2x+" + phase + ")")
    assert parent != PARENT
    with pytest.raises(UnsupportedCondition):
        analysis(parent=parent)


@pytest.mark.parametrize("coefficient", ["3x", r"\frac{3x}{2}", "x"])
def test_unreviewed_parent_angle_scale_is_rejected(coefficient):
    parent = PARENT.replace(
        r"\cos (2x+\frac{\pi}{4})", r"\cos (" + coefficient + r"+\frac{\pi}{4})"
    )
    assert parent != PARENT
    with pytest.raises(UnsupportedCondition):
        analysis(parent=parent)


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{4\cos 2x-2\sin 2x}=2\cos x+1",
        r"\sqrt{4\cos 2x-2\sin 2x}=2\cos^2 x",
        r"\frac{\sqrt{4\cos 2x-2\sin 2x}}{1+\sin x}=2\cos x",
        r"\sqrt{4\cos 2x-2\sin 2x}+\sqrt{\sin x}=2\cos x",
    ],
)
def test_unreviewed_right_sides_poles_and_multiple_radicals_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_radical(formula, "safe_square", parent_html=PARENT)


@pytest.mark.parametrize("expression", [S, C + 1, S * C * C, 1 / C])
def test_nonquadratic_double_angle_projection_is_not_guessed(expression):
    with pytest.raises(UnsupportedCondition):
        double_polynomial(expression)


def test_logarithmic_constant_root_does_not_become_a_variable_radical_method():
    assert (
        kind(
            r'<p><span data-inline-latex="\log_{\sqrt{2}\sin x}(1+\cos x)=2\iff 1+\cos x=2\sin^2x"></span></p>'
        )
        == ""
    )


def test_unknown_circle_and_changed_interval_cannot_reuse_the_source():
    ctx = deepcopy(CTX)
    a = ctx["normalized_content"]["assets"][0]
    a["asset_id"] = "unknown"
    a["url"] = "/assets/unknown"
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
    entry = deepcopy(CIRCLES[AID])
    entry["bounds"][0] = "-3"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis())


def test_catalog_registration_uses_the_existing_shared_handler():
    p = get_group_profile(CASE["group"])
    assert p.source_group_id == DATA["group"]["uuid"]
    assert p.snapshot_theme_id == DATA["group"]["theme_uuid"]
    assert p.group_order_index == DATA["group"]["order_index"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
