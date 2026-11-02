"""Retain a common zero factor and select roots against exact Euler bounds."""

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

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_input import endpoint
from solution_runner.pipelines.equations.exam_scalar import e_bounds, enclose
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
    select_euler,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_euler_square.json"
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
def test_original_equation_has_only_cosine_zeros_and_exact_euler_selection(c):
    a = analysis(c)
    assert a.bounds == (-sp.E / sp.pi, 1, True, True)
    assert a.square_difference.rhs == sp.sqrt(7) * C
    assert a.residues == (R(1, 2), R(3, 2))
    assert a.selected == (-R(1, 2), R(1, 2))
    assert a.series == ((R(1, 2), 1),)
    assert any(
        b.variable == S and b.candidates == (sp.sqrt(7) / 2,) and not b.values
        for b in a.branches
    )
    with mp.workdps(65):
        for n in range(-384, 385):
            q = R(n, 48)
            x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
            value = (
                mp.sin(mp.pi / 4 + x) ** 2
                - mp.sin(mp.pi / 4 - x) ** 2
                - mp.sqrt(7) * mp.cos(x)
            )
            assert (abs(value) < mp.mpf("1e-50")) == (q % 1 == R(1, 2))
    html = plan(c).solution_html
    assert "Это значение не входит в отрезок" in html and r"\frac{\sqrt{7}}{2}" in html
    assert html.index("разности и суммы") < html.index("Произведение равно нулю")
    assert "- e" in html and "[-e;\\pi]" in html


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
def test_original_native_circle_has_both_roots_and_immutable_source_hash(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert (
        hashlib.sha256(raw).hexdigest()
        == e["sha256"]
        == "44704e90aa8b2fb8c66cb921d6a3a2efcd3cdcc0038f94d9a07bdb28a37c364f"
    )
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    assert len(e["green_markers"]) == 2 and not e.get("corrected_file")
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
    changed["bounds"][0] = {"e": "-2"}
    with pytest.raises(UnsupportedCondition):
        validate(changed, analysis(c))


@pytest.mark.parametrize("terms", [1, 8, 16, 32, 64, 128])
def test_rational_euler_enclosures_contain_independent_high_precision_constant(terms):
    lo, hi = e_bounds(terms)
    with mp.workdps(300):
        assert (
            mp.mpf(lo.numerator) / lo.denominator
            < mp.e
            < mp.mpf(hi.numerator) / hi.denominator
        )
    if terms > 1:
        old_lo, old_hi = e_bounds(terms // 2)
        assert old_lo < lo < hi < old_hi


@pytest.mark.parametrize("terms", [0, -1, 129, True, "16"])
def test_euler_series_rejects_unreviewed_term_limits(terms):
    with pytest.raises(UnsupportedCondition):
        e_bounds(terms)


@pytest.mark.parametrize("text,expected", [("e", sp.E), ("+e", sp.E), ("-e", -sp.E)])
def test_only_explicit_euler_endpoint_literals_are_read(text, expected):
    assert endpoint(text) == expected


@pytest.mark.parametrize("text", ["E", "exp(1)", "e+x", "e^x", "e/2", "z"])
def test_arbitrary_endpoint_expressions_are_not_evaluated(text):
    with pytest.raises(UnsupportedCondition):
        endpoint(text)


@pytest.mark.parametrize(
    "value",
    [{"e": "0"}, {"e": "1001"}, {"e": "e"}, {"e": "1/0"}, {"e": "1", "scalar": "0"}],
)
def test_euler_circle_coordinates_require_bounded_rational_coefficient(value):
    with pytest.raises(UnsupportedCondition):
        decode(value)


def test_euler_comparisons_use_exact_enclosures_and_reject_variable_named_e():
    assert decode({"e": "-1"}) == -sp.E / sp.pi
    assert compare_q(sp.E / sp.pi, R(1, 2)) == 1
    assert compare_q(sp.E / sp.pi, 1) == -1
    assert compare_q(-sp.E / sp.pi, -R(1, 2)) == -1
    assert compare_q(sp.E / sp.pi, sp.E / sp.pi) == 0
    with pytest.raises(UnsupportedCondition):
        enclose(sp.Symbol("e"))


@pytest.mark.parametrize("closed", [True, False])
def test_exact_selection_respects_open_rational_endpoint_and_integer_bounds(closed):
    roots, trace = select(((R(1, 2), 1),), (-sp.E / sp.pi, R(1, 2), True, closed))
    assert roots == ((-R(1, 2), R(1, 2)) if closed else (-R(1, 2),))
    assert trace[0][-1] == roots
    assert select_euler(((0, 1),), (0, 2, closed, closed))[0] == (
        (0, 1, 2) if closed else (1,)
    )


@pytest.mark.parametrize(
    "series,bounds",
    [
        (((sp.acos(R(1, 3)) / sp.pi, 1),), (-sp.E / sp.pi, 1, True, True)),
        (((0, 0),), (-sp.E / sp.pi, 1, True, True)),
        (((0, sp.E),), (-sp.E / sp.pi, 1, True, True)),
        (((0, 1),), ("-e", 1, True, True)),
    ],
)
def test_euler_selection_rejects_unparsed_bounds_and_nonrational_series(series, bounds):
    with pytest.raises(UnsupportedCondition):
        select_euler(series, bounds)


@pytest.mark.parametrize(
    "rhs,expected",
    [
        (r"\sqrt{7}\cos x", ("1/2", "3/2")),
        (r"\sqrt{7}\sin x", ("0", "1")),
        (r"-\sqrt{7}\cos x", ("1/2", "3/2")),
        (r"\frac{2}{2}\cos x", None),
    ],
)
def test_shared_square_difference_retains_common_factor_for_both_linear_rhs_functions(
    rhs, expected
):
    a = analysis(CASES[0], r"\sin^2(\frac{\pi}{4}+x)=\sin^2(\frac{\pi}{4}-x)+" + rhs)
    assert a.square_difference.rhs != 0 and not a.square_difference.general
    if expected:
        assert a.residues == tuple(map(R, expected))
    else:
        assert len(a.residues) == 4


def test_right_hand_term_order_does_not_change_difference_certificate():
    a = analysis(
        CASES[0], r"\sin^2(\frac{\pi}{4}+x)=\sqrt{7}\cos x+\sin^2(\frac{\pi}{4}-x)"
    )
    assert a.square_difference == analysis(CASES[0]).square_difference


def test_non_tabular_rhs_level_is_rejected_instead_of_inventing_inverse_roots():
    with pytest.raises(UnsupportedCondition):
        analysis(
            CASES[0],
            r"\sin^2(\frac{\pi}{4}+x)=\sin^2(\frac{\pi}{4}-x)+\frac{1}{2}\cos x",
        )
