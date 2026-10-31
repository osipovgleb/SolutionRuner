"""Original domains, half angles and source parameters without stored answers or SVGs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_mixed_methods.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
EXPECTED = {
    "484545": ("1/4 5/4", "5/4"),
    "527633": (
        "0 5/32 7/32 13/32 15/32 21/32 23/32 29/32 31/32 1 37/32 39/32 45/32 47/32 53/32 55/32 61/32 63/32",
        "-43/32 -41/32 -35/32 -33/32 -1",
    ),
    "553829": ("3/2", "3/2 7/2"),
    "562175": (
        "0 1/18 1/6 5/18 1/3 7/18 1/2 11/18 2/3 13/18 5/6 17/18 1 19/18 7/6 23/18 4/3 25/18 3/2 29/18 5/3 31/18 11/6 35/18",
        "-13/18 -2/3 -11/18 -1/2 -7/18 -1/3 -5/18",
    ),
    "562186": (
        "0 5/24 1/4 7/24 1/2 17/24 3/4 19/24 1 29/24 5/4 31/24 3/2 41/24 7/4 43/24",
        "65/24 11/4 67/24 3 77/24 13/4 79/24",
    ),
    "620775": ("1/12 1/6 7/12 2/3 13/12 7/6 19/12 5/3", "1/12 1/6"),
    "633390": ("1/2", "9/2"),
}
ORIGINAL = {
    "484545": sp.Abs(c + s) - sp.sqrt(2) * sp.sin(2 * X),
    "527633": sp.cos(9 * X) - sp.cos(7 * X) - sp.sqrt(2) * s,
    "553829": sp.sin(3 * X) * sp.cos(4 * X) - 1,
    "562175": sp.cos(3 * X) * sp.sin(3 * X)
    - sp.cos(sp.pi / 3) * sp.cos(12 * X + 3 * sp.pi / 2),
    "562186": sp.cos(2 * X) * sp.sin(2 * X) * sp.sin(2 * sp.pi / 3)
    - sp.cos(8 * X - 3 * sp.pi / 2) / 4,
    "620775": sp.sqrt(3) * sp.sin(2 * X) ** 2
    - 2 * sp.sin(4 * X)
    + sp.sqrt(3) * sp.cos(2 * X) ** 2,
    "633390": s**4 + (s - 2) ** 4 - 2,
}
POLES = {task: () for task in ORIGINAL}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(example):
    return next(
        s["html"]
        for s in case(example["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example):
    _, f, i, b = read(example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


def rational(text):
    return tuple(map(sp.Rational, text.split())) if isinstance(text, str) else text


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_the_existing_handler_and_actual_catalog_order(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 8, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_root_sets_are_independently_expected(example):
    task = example["task"]
    a = analysis(example)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == rational(EXPECTED[task][0])
    assert a.selected == rational(EXPECTED[task][1])
    for q in (*roots, *a.selected):
        angle = q * sp.pi
        assert all(
            abs(complex(p.subs(X, angle).evalf(40))) > 1e-20 for p in POLES[task]
        )
        assert abs(complex(ORIGINAL[task].subs(X, angle).evalf(40))) < 1e-30
    # Check a dense independent lattice, including forbidden points and roots outside b).
    for k in range(384):
        q = sp.Rational(k, 192)
        angle = q * sp.pi
        allowed = all(
            abs(complex(p.subs(X, angle).evalf(30))) > 1e-18 for p in POLES[task]
        )
        zero = allowed and abs(complex(ORIGINAL[task].subs(X, angle).evalf(30))) < 1e-18
        assert (q in roots) == zero


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert (
        example["context"] == original and not original["normalized_content"]["assets"]
    )
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>не использовать</p>"
    assert (plan(example, changed).answer, plan(example, changed).solution_html) == (
        p.answer,
        p.solution_html,
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(example, changed).transformations == ()
    handler = get_handler(get_group_profile(example["group"]).content_rule_key)
    assert handler.diagram_specs(original) == ()
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")


def test_literal_radian_bounds_use_neighbor_indices_and_certified_comparisons():
    from solution_runner.pipelines.equations.exam_trigonometric_neighbors import certify

    first = analysis(case("484545"))
    assert first.selection_method == "neighbors" and first.bounds[:2] == (
        3 / sp.pi,
        5 / sp.pi,
    )
    second = analysis(case("620775"))
    assert second.selection_method == "neighbors" and second.bounds[:2] == (
        -1 / sp.pi,
        1 / sp.pi,
    )
    assert certify(((sp.S.Zero, sp.S.One),), (0, 2, False, False))[0] == (1,)
    assert certify(((sp.S.Zero, sp.S.One),), (0, 2, True, True))[0] == (0, 1, 2)
    assert (
        certify(
            ((sp.S.Zero, sp.S.One),), (sp.Rational(1, 4), sp.Rational(3, 4), True, True)
        )[0]
        == ()
    )
    for example in (case("484545"), case("620775")):
        p = plan(example)
        assert r"3<\pi<\frac{22}{7}" in [
            n["data-inline-latex"]
            for n in BeautifulSoup(p.solution_html, "html.parser").select(
                "[data-inline-latex]"
            )
        ]
        assert (
            "Все меньшие индексы" in p.solution_html
            and "Все большие индексы" in p.solution_html
        )


def test_squaring_keeps_the_right_side_sign_and_explains_the_extraneous_level():
    a = analysis(case("484545"))
    p = plan(case("484545"))
    assert a.absolute_square and a.scale == 2
    assert set(a.branches[0].candidates) == {sp.S.One, -sp.Rational(1, 2)}
    assert sp.Rational(7, 12) not in select(a.series, (0, 2, True, False))[0]
    assert "нарушает знак правой части" in p.solution_html
    assert r"\cosx" not in p.solution_html and r"\sinx" not in p.solution_html


def test_extremal_sum_intersects_the_two_conditions_instead_of_uniting_their_roots():
    a = analysis(case("553829"))
    p = plan(case("553829"))
    assert a.extremum and a.series == ((-sp.Rational(1, 2), sp.Integer(2)),)
    assert r"n=7 k - 2" in p.solution_html
    assert sp.Rational(1, 14) not in select(a.series, (0, 2, True, False))[0]
    assert "обоим уравнениям одновременно" in p.solution_html


def test_sine_equality_retains_the_negative_period_and_reverses_index_inequalities():
    a = analysis(case("562175"))
    p = plan(case("562175"))
    assert a.sine_pair[-1] and a.signed_series[0] == (0, -sp.Rational(1, 3))
    assert r"\frac{3}{4}\le k \le\frac{9}{4}" in p.solution_html
    assert r"x=- \frac{\pi k}{3}" in p.answer
    child = analysis(case("562186"))
    child_plan = plan(case("562186"))
    assert not child.sine_pair[-1] and not child.signed_series
    assert "коэффициенты синусов различны" in child_plan.solution_html
    assert sp.Integer(3) in child.selected
    assert r"\frac{\pi}{4}-k" not in child_plan.answer


def test_the_sine_double_angle_method_avoids_an_unrelated_tangent_factorization():
    a = analysis(case("620775"))
    p = plan(case("620775"))
    assert a.sine_double and a.scale == 4
    assert r"\tg" not in p.solution_html and r"\sin 4 x" in p.solution_html
    assert a.series == (
        (sp.Rational(1, 12), sp.Rational(1, 2)),
        (sp.Rational(1, 6), sp.Rational(1, 2)),
    )


def test_parent_offsets_are_certified_and_reused_in_the_original_order():
    a = analysis(case("527633"))
    p = plan(case("527633"))
    assert a.series == (
        (0, 1),
        (-sp.Rational(1, 32), sp.Rational(1, 4)),
        (-sp.Rational(3, 32), sp.Rational(1, 4)),
    )
    assert a.series_aligned and "перенумеруем целые индексы" in p.solution_html


def test_both_quartic_methods_remain_in_order_with_the_shifted_substitution():
    a = analysis(case("633390"))
    p = plan(case("633390"))
    assert a.centered_power[-1] and not a.alternative.centered_power[-1]
    soup = BeautifulSoup(p.solution_html, "html.parser")
    primary = soup.select("li")[0]
    assert r"t + 1" in str(primary) and r"t^{4} + 12 t^{2}" in str(primary)
    assert p.solution_html.index("Приведём другое решение") > p.solution_html.index(
        'data-list-marker="б)"'
    )
    assert "строго положител" in p.solution_html


@pytest.mark.parametrize(
    "formula",
    (
        r"|\cos x+\sin x|=-\sqrt{2}\sin 2x",
        r"|\cos x+\sin x|=\sqrt{2}\sin 3x",
        r"|\cos x+\sin x|=1/\sin x",
    ),
)
def test_absolute_square_fails_closed_when_the_original_sign_certificate_is_missing(
    formula,
):
    from solution_runner.pipelines.equations.exam_trigonometric_absolute_square import (
        compile_square,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_compile import S
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    with pytest.raises(UnsupportedCondition):
        compile_square(formula, S, 2)


@pytest.mark.parametrize(
    "formula",
    (r"\sin 3x\cos 4x=\frac{9}{10}", r"\sin 2x\cos 3x=1", r"\sin 3x\cos 13x=1"),
)
def test_extremum_proof_requires_the_exact_bound_and_the_full_intersection_certificate(
    formula,
):
    from solution_runner.pipelines.equations.exam_trigonometric_extremum import (
        compile_extremum,
    )
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    with pytest.raises(UnsupportedCondition):
        compile_extremum(formula)


@pytest.mark.parametrize(
    "formula",
    (r"\sin 3x=\sin 7x", r"\sin (3x+\frac{\pi}{7})=\sin 6x", r"\sin 6x=\sin 12x+1"),
)
def test_sine_pair_refuses_unreviewed_angles_shifts_and_added_terms(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_sine_pair import (
        compile_pair,
    )
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    with pytest.raises(UnsupportedCondition):
        compile_pair(formula)
