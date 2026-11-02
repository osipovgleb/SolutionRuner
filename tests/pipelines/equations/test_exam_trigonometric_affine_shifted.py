"""Keep original ratio poles and certify shifted-square double-angle reductions."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from dataclasses import replace
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
from solution_runner.pipelines.equations.exam_trigonometric_combination import (
    branches as combination_branches,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_sine_double import (
    shifted_square,
    shifted_square_parent,
)
from solution_runner.pipelines.equations.exam_trigonometric_style import preference
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_affine_shifted.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = DATA["expected"]


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
def test_complete_and_selected_roots_follow_independent_original_equations(c):
    a = analysis(c)
    expected = EXPECTED[c["task"]]
    full = tuple(map(R, expected["full"]))
    assert a.selected == tuple(map(R, expected["selected"]))
    assert select(a.series, (0, 2, True, False))[0] == full
    with mp.workdps(65):
        for n in range(-432, 433):
            q = R(n, 72)
            x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
            if c["task"] == "692248":
                if (2 * q).is_Integer:
                    continue
                s, co = mp.sin(x), mp.cos(x)
                value = 3 * co / s + 1 / co - s / co - mp.sqrt(3) / s
            else:
                value = (
                    8 * mp.sin(x + 7 * mp.pi / 12) ** 2
                    - 2 * mp.sqrt(3) * mp.cos(2 * x)
                    - 5
                )
            assert (abs(value) < mp.mpf("1e-45")) == (q % 2 in full)
    if c["task"] == "692248":
        assert set(a.poles) == {S, C} and not any(b.impossible for b in a.branches)
        assert a.branches[1].angle_shift == R(1, 3) and a.branches[1].residues == (
            R(11, 6),
        )
    else:
        assert preference(parent(c)) == ("sin", 2)
        assert a.sine_double[2] == (8, -2 * sp.sqrt(3), 5, R(7, 12)) and a.scale == 2


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_circle_roots_excluded_crosses_and_original_bytes_are_audited(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    nodes = list(ET.fromstring(raw).iter())
    paths = {n.get("d") for n in nodes if n.tag.endswith("path")}
    validate(entry, analysis(c))
    assert {decode(p["angle"]) for p in entry["green_markers"]} == set(
        map(R, EXPECTED[c["task"]]["full"])
    )
    for p in entry["green_markers"] + entry["excluded_markers"]:
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
        for cross in p.get("cross_segments", []):
            assert any(
                n.tag.endswith(cross["tag"]) and dict(n.attrib) == cross["attributes"]
                for n in nodes
            )
            assert (
                math.hypot(cross["center"][0] - p["x"], cross["center"][1] - p["y"]) < 2
            )
    if c["task"] == "692248":
        assert len(entry["excluded_markers"]) == 1
        assert entry["excluded_markers"][0]["angle"] == "1/2"
        assert len(entry["excluded_markers"][0]["cross_segments"]) == 2
        assert sp.cos(decode(entry["excluded_markers"][0]["angle"]) * sp.pi) == 0
    else:
        assert entry["excluded_markers"] == []


def case(task):
    return next(c for c in CASES if c["task"] == task)


def test_ratio_proof_multiplies_only_on_original_domain_and_excludes_the_extra_series():
    html = plan(case("692248")).solution_html
    assert (
        html.index("область определения")
        < html.index("умножим обе части")
        < html.index("Произведение равно нулю")
    )
    assert "Эта серия нарушает исходную область определения и исключается" in html
    assert r"\cos (\frac{\pi}{2}+2\pi k)" in html and r"\frac{\pi}{3}" in html
    assert "После проверки исходной области определения оставляем" not in html


def test_shifted_square_proof_explains_the_source_phase_lowering_and_cancellation_in_parent_order():
    html = plan(case("521994")).solution_html
    assert (
        html.index("формулу приведения")
        < html.index("Понизим степень")
        < html.index("Раскроем косинус суммы")
    )
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any(f.count(r"\sin") == 2 and r"\cos" in f for f in forms)
    assert any(
        r"\frac{7 \pi}{12}" in f and r"\cos" in f and r"\sin" in f for f in forms
    )
    assert any(r"\cos^{2}" in f and r"\frac{\pi}{12}" in f and "=" in f for f in forms)
    assert any(
        r"\frac{\pi}{6}" in f and r"\sqrt{3}" in f and r"\sin" in f for f in forms
    )
    assert r"4 - 2 \sin{\left(2 x \right)}=5" in forms


@pytest.mark.parametrize(
    "formula,full",
    [
        (
            r"4\sin^2(\frac{7\pi}{12}+x)-\sqrt{3}\cos 2x=\frac{5}{2}",
            ("7/12", "11/12", "19/12", "23/12"),
        ),
        (
            r"8\sin^2(\frac{5\pi}{12}+x)-2\sqrt{3}\cos 2x=5",
            ("1/12", "5/12", "13/12", "17/12"),
        ),
        (
            r"8\sin^2(\frac{\pi}{12}+x)+2\sqrt{3}\cos 2x=5",
            ("1/12", "5/12", "13/12", "17/12"),
        ),
    ],
)
def test_shifted_square_certificate_adapts_coefficients_and_twelfth_turns(
    formula, full
):
    a = analysis(case("521994"), formula)
    assert select(a.series, (0, 2, True, False))[0] == tuple(map(R, full))
    assert len(a.sine_double) == 3


@pytest.mark.parametrize(
    "formula",
    [
        r"8\sin^2(\frac{7\pi}{12}+x)-\sqrt{3}\cos 2x=5",
        r"8\sin^2(\frac{7\pi}{12}+x)-2\sqrt{3}\cos 2x+x=5",
        r"8\sin^2(\frac{7\pi}{12}+2x)-2\sqrt{3}\cos 2x=5",
        r"8\sin^2(\frac{7\pi}{12}+x)-2\sqrt{3}\cos 3x=5",
        r"8\sin^2(\frac{\pi}{2}+x)+4\cos 2x=5",
        r"\frac{8\sin^2(\frac{7\pi}{12}+x)-2\sqrt{3}\cos 2x}{\sin x}=5",
    ],
)
def test_shifted_square_rejects_uncancelled_cosine_foreign_angles_and_original_poles(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        shifted_square(formula)


def test_shifted_square_parent_needs_the_reviewed_exact_quarter_turn_identity():
    p = parent(case("521994"))
    assert shifted_square_parent(p) == (R(7, 12), R(1, 12))
    assert (
        shifted_square_parent("<p>Понизим степень и применим формулу приведения.</p>")
        is None
    )
    assert (
        shifted_square_parent(p.replace(r"\frac{7\pi}{12}", r"\frac{5\pi}{12}", 1))
        is None
    )


@pytest.mark.parametrize(
    "raw",
    [(S + C - 1) * (S - C - 1), (S + C) * (S - C) ** 2, (S + C) * (3 * S + 4 * C - 1)],
)
def test_combination_rejects_unsupported_factorizations_and_unknown_phases(raw):
    with pytest.raises(UnsupportedCondition):
        combination_branches(sp.expand(raw))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_circle_and_changed_interval_cannot_reuse_source(c):
    ctx = deepcopy(c["context"])
    asset = ctx["normalized_content"]["assets"][0]
    asset["asset_id"] = "unknown-circle"
    asset["url"] = "/assets/unknown-circle"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    entry = deepcopy(
        CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    entry["bounds"][0] = "-10"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_source_root_on_interval_boundary_respects_closed_and_open_endpoints(c):
    a = analysis(c)
    left, right = tuple(map(R, EXPECTED[c["task"]]["selected"]))[:2]
    assert select(a.series, (left, right, True, False))[0] == (left,)
    assert select(a.series, (left, right, False, True))[0] == (right,)


def test_missing_projection_or_conflicting_special_method_fails_closed():
    from solution_runner.pipelines.equations.exam_trigonometric_methods import Equation
    from solution_runner.pipelines.equations.exam_trigonometric_sine_double import (
        prepare,
    )

    c = case("521994")
    a = analysis(c)
    formula = read(c["context"])[1]
    equation = Equation(a.sine_double[0], (), sp.S.One)
    for changed in [replace(equation, poles=(S,)), replace(equation, raw=S + C)]:
        with pytest.raises(UnsupportedCondition):
            prepare(changed, S, 2, formula=formula, parent_html=parent(c))


def test_previously_supported_two_homogeneous_factors_are_kept():
    _raw, branches = combination_branches(sp.expand((S + C) * (S - C)))
    assert {q for b in branches for q in b.residues} == set(
        map(R, ("1/4", "3/4", "5/4", "7/4"))
    )


def test_already_projected_equation_keeps_an_exact_rational_source_scale():
    from solution_runner.pipelines.equations.exam_trigonometric_methods import Equation
    from solution_runner.pipelines.equations.exam_trigonometric_sine_double import (
        prepare,
    )

    c = case("521994")
    result = prepare(
        Equation(2 * S - 1, (), 2),
        S,
        2,
        formula=r"8\sin^2(\frac{5\pi}{12}+x)-2\sqrt{3}\cos 2x=5",
        parent_html=parent(c),
    )
    assert result.sine_double[1] == 1
    assert isinstance(result.sine_double[1], sp.Rational)
