"""Difference of squares, sum of cubes, and independent parent methods."""

import gzip
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    canonical,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.equations.exam_trigonometric_symmetric import V, prepare
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_algebraic_identities.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "555715": "3 7/2 4 9/2",
    "555895": "5/2 3 7/2 4",
    "555967": "2 7/3 3",
    "556029": "-2 -5/4 -1",
    "559407": "-5/2 -2 -3/2 -1",
    "559601": "3/2 2 5/2 3",
    "562150": "-9/4 -13/6 -5/4",
    "562693": "-1/4 1/4",
    "562950": "5/2",
}
RESIDUES = {
    "555715": "0 1/2 1 3/2",
    "555895": "0 1/2 1 3/2",
    "555967": "0 1/3 1 4/3",
    "556029": "0 3/4 1 7/4",
    "559407": "0 1/2 1 3/2",
    "559601": "0 1/2 1 3/2",
    "562150": "3/4 7/6 7/4 11/6",
    "562693": "1/4 3/4 5/4 7/4",
    "562950": "0 1/2",
}
ORIGINAL = {
    "555715": sp.cos(sp.pi / 4 - X) ** 2 - sp.cos(sp.pi / 4 + X) ** 2,
    "555895": sp.sin(sp.pi / 4 - X) ** 2 - sp.sin(sp.pi / 4 + X) ** 2,
    "559407": sp.cos(2 * sp.pi / 3 - X) ** 2 - sp.cos(2 * sp.pi / 3 + X) ** 2,
    "559601": sp.cos(5 * sp.pi / 6 - X) ** 2 - sp.cos(5 * sp.pi / 6 + X) ** 2,
    "555967": 2 * s * s - sp.sqrt(3) * sp.sin(2 * X),
    "556029": sp.sin(2 * X) + 2 * s * s,
    "562150": sp.cos(2 * X) - sp.sin(2 * X) - c - s - 1,
    "562693": c**6 + s**6 - sp.sin(2 * X) ** 2 / 4,
    "562950": s**3 + c**3 - s * s - c * c,
}
IDENTITY = {
    "555715": sp.sin(2 * X),
    "555895": -sp.sin(2 * X),
    "559407": -sp.sqrt(3) * sp.sin(2 * X) / 2,
    "559601": -sp.sqrt(3) * sp.sin(2 * X) / 2,
    "555967": 2 * s * (s - sp.sqrt(3) * c),
    "556029": 2 * s * (s + c),
    "562150": -(s + c) * (2 * s + 1),
    "562693": sp.cos(2 * X) ** 2,
    "562950": s * s * (s - 1) + c * c * (c - 1),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for p in CASES
        if p["task"] == c["group"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_algebra_and_complete_and_selected_roots_are_independent(c):
    task = c["task"]
    a = analysis(c)
    polynomial = sp.expand(sp.expand_trig(ORIGINAL[task] - IDENTITY[task])).xreplace(
        {sp.sin(X): S, sp.cos(X): C}
    )
    assert sp.rem(polynomial, S * S + C * C - 1, S) == 0
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    for q in a.selected:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize(
    "c", [c for c in CASES if c["task"] != "562150"], ids=lambda c: c["task"]
)
def test_reviewed_circles_keep_exact_bytes_selected_labels_and_boundary_semantics(c):
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[asset]
    assert (
        hashlib.sha256(
            gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
        ).hexdigest()
        == e["sha256"]
    )
    expected = (
        ordered(turn(q) for q in a.selected)
        if c["task"] == "562950"
        else tuple(map(sp.Rational, RESIDUES[c["task"]].split()))
    )
    assert ordered(decode(m["angle"]) for m in e["green_markers"]) == expected
    assert tuple(decode(q) for q in e["labels"]) == a.selected
    if c["task"] == "562693":
        assert next(m for m in e["green_markers"] if m["angle"] == "5/4")[
            "selection_status"
        ] == "open_boundary" and a.bounds[2:] == (False, True)
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


@pytest.mark.parametrize("task", ["555715", "555895", "559407", "559601"])
def test_square_difference_retains_the_parent_product_and_merged_n_family(task):
    a = analysis(case(task))
    assert a.square_difference is not None and a.square_difference.parameter == "n"
    assert a.series == ((0, sp.Rational(1, 2)),)
    p = plan(case(task))
    assert r"x=\frac{\pi n}{2}" in p.answer and r"n\in\mathbb Z" in p.answer
    assert (
        "разность квадратов" in p.solution_html
        and "суммы и разности" in p.solution_html
    )
    assert r"\sin2x=0" in p.solution_html and "D=" not in p.solution_html


def test_broken_child_answer_and_solution_do_not_affect_the_correct_half_pi_period():
    p = plan(case("555895"))
    assert r"x=\frac{\pi n}{2}" in p.answer
    for k in range(-10, 11):
        assert ORIGINAL["555895"].subs(X, k * sp.pi / 2) == 0


def test_integer_parameter_is_read_from_the_root_family_not_the_word_sine():
    from solution_runner.pipelines.equations.exam_trigonometric_square_difference import (
        parameter,
    )

    html = '<span data-inline-latex="\\sin2x=0"></span><span data-inline-latex="x=\\frac{\\pi k}{2}"></span>'
    assert parameter(html) == "k"


def test_sixth_powers_use_sum_of_cubes_and_sine_square_without_discriminant():
    a = analysis(case("562693"))
    assert (
        a.power_angle == 1
        and a.scale == 2
        and a.series == ((sp.Rational(1, 4), sp.Rational(1, 2)),)
    )
    html = plan(case("562693")).solution_html
    assert (
        "суммы кубов" in html and "периода квадрата синуса" in html and "D=" not in html
    )
    assert -sp.Rational(3, 4) not in a.selected and sp.Rational(1, 2) not in a.selected


def test_unit_circle_factorization_keeps_the_homogeneous_branch_first():
    a = analysis(case("562150"))
    assert a.factored_source is not None
    assert a.branches[0].original is not None and a.series[0] == (-sp.Rational(1, 4), 1)
    html = plan(case("562150")).solution_html
    assert "неравенства для целого параметра" in html and "только в этой ветви" in html
    assert not BeautifulSoup(html, "html.parser").find("img")


def test_both_parent_methods_are_complete_independent_and_keep_the_single_figure():
    c = case("562950")
    a = analysis(c)
    assert a.alternative is not None
    assert not a.symmetric.nonpositive and a.alternative.symmetric.nonpositive
    assert sp.expand(-2 * a.symmetric.polynomial) == sp.expand((V - 1) ** 2 * (V + 2))
    assert (
        canonical(a.series) == canonical(a.alternative.series) == (0, sp.Rational(1, 2))
    )
    html = plan(c).solution_html
    assert (
        html.index("замены суммы")
        < html.index("Приведём другое решение")
        < html.index("Каждое слагаемое неположительно")
    )
    assert "t=" in html and r"\sqrt2" in html and "(0;1);(1;0)" in html
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1


@pytest.mark.parametrize("angle", [r"0", r"\frac{\pi}{2}", r"\frac{\pi}{7}"])
def test_degenerate_and_unreviewed_square_difference_shifts_fail_closed(angle):
    formula = r"\cos^2(" + angle + r"-x)=\cos^2(" + angle + r"+x)"
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, 2, difference=True)


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin x=0",
        r"\cos^2(x/2-\frac{\pi}{4})=\cos^2(x/2+\frac{\pi}{4})",
        r"\sin^2(\frac{\pi}{4}-x)=\cos^2(\frac{\pi}{4}+x)",
    ],
)
def test_parent_square_difference_cannot_silently_use_an_unrelated_method(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, 2, difference=True)


@pytest.mark.parametrize("formula", [r"\sin^6 x+\cos^6(2x)=1", r"2\sin^6 x+\cos^6 x=1"])
def test_sixth_powers_need_paired_angles_and_equal_coefficients(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, 2)


def test_sign_method_rejects_an_unrelated_symmetric_cubic():
    from solution_runner.pipelines.equations.exam_trigonometric_methods import Equation

    c = case("562950")
    html = next(
        s["html"]
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    from solution_runner.pipelines.equations.exam_trigonometric_methods import methods

    _, alternative = methods(html)
    with pytest.raises(UnsupportedCondition):
        prepare(Equation(S**3 + C**3 - 2, (), sp.S.One), alternative, 0)


@pytest.mark.parametrize(
    "formula, expected",
    [
        (r"\cos^6 x-\sin^6 x=0", (C**3 + 3 * C) / 4),
        (r"\cos^6 x+2\sin^6 x=1", (-(C**3) + 9 * C**2 - 3 * C - 5) / 8),
        (r"\cos^6 x+\sin^6 x=1", 3 * (C * C - 1) / 4),
    ],
)
def test_existing_cosine_double_angle_reduction_of_sixth_powers_is_preserved(
    formula, expected
):
    equation = compile_reviewed(formula, C, 2)
    assert sp.expand(equation.raw - expected) == 0 and equation.scale == 2
