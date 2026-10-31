"""Original domains, half angles and source parameters without stored answers or SVGs."""

import json
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_folding import common_scale
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    parse_equation,
)
from solution_runner.pipelines.equations.exam_trigonometric_parameters import names
from solution_runner.pipelines.equations.trig_symbolic_parser import SymbolicAtom
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_assetless_domains.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
EXPECTED = {
    "633751": (
        (sp.Rational(1, 2) + sp.acos(sp.Rational(3, 4)) / sp.pi,),
        (-sp.Rational(7, 2) + sp.acos(sp.Rational(3, 4)) / sp.pi,),
    ),
    "637084": ("0 1", "-5 -4"),
    "646081": ("1/6 5/6", "-23/6 -19/6 -11/6 -7/6"),
    "668795": ("0 4/3", "8/3"),
    "677685": ("3/8 7/8 11/8 15/8", "-9/8 -5/8 -1/8 3/8"),
    "695735": (
        "1/9 1/6 1/3 1/2 5/9 7/9 5/6 7/6 11/9 13/9 3/2 5/3 11/6 17/9",
        "1/9 1/6 1/3 1/2 5/9 7/9 5/6",
    ),
}
ORIGINAL = {
    "633751": (6 * s - 2 * sp.cos(2 * X) - 4 * c * c - 3) / (sp.sqrt(7) * s - 3 * c),
    "637084": (2 * sp.sin(sp.pi / 4 - X) ** 2 - c * c) / (2 * sp.tan(X) - 4),
    "646081": sp.tan(X) ** 2 - 1 / c**2 + 2 * s * s + s,
    "668795": c / sp.cos(X + sp.pi / 3) - sp.cos(X / 2) / sp.sin(sp.pi / 6 - X),
    "677685": 1 / sp.tan(X) + 1 / sp.cot(X) - 2 * sp.cot(X) - 2,
    "695735": sp.tan(2 * X) + 1 / s - sp.cot(X) - 1 / sp.sin(5 * X),
}
POLES = {
    "633751": (sp.sqrt(7) * s - 3 * c,),
    "637084": (c, 2 * s - 4 * c),
    "646081": (c,),
    "668795": (sp.cos(X + sp.pi / 3), sp.sin(sp.pi / 6 - X)),
    "677685": (s, c),
    "695735": (sp.cos(2 * X), s, sp.sin(5 * X)),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(example):
    return next(
        s["html"]
        for s in example["context"]["normalized_content"]["sections"]
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
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


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
    for k in range(144):
        q = sp.Rational(k, 72)
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


def test_half_angle_base_is_independent_of_atom_order_and_does_not_truncate_multiples():
    for coefficients in set(
        permutations((sp.S.One, sp.S.One, sp.Rational(1, 2), sp.S.One))
    ):
        atoms = {
            i: SymbolicAtom("cos", v, 0, "x", "") for i, v in enumerate(coefficients)
        }
        assert common_scale(atoms) == sp.Rational(1, 2)
    a = analysis(case("668795"))
    assert a.scale == sp.Rational(1, 2) and a.series == (
        (sp.S.Zero, sp.Rational(4, 3)),
    )
    assert a.parameter == "l" and a.family_parameters == ("l",)
    assert "l" in plan(case("668795")).answer
    assert a.selected != (sp.Integer(2),)


def test_two_squares_preserves_plus_minus_branches_and_both_original_poles():
    a = analysis(case("637084"))
    p = plan(case("637084"))
    assert a.square_difference.general and len(a.poles) == 2
    text = BeautifulSoup(p.solution_html, "html.parser").get_text(" ")
    assert "Квадраты двух чисел равны" in text and "любое любое" not in text
    assert any(not b.values for b in a.branches)


def test_distinct_family_letters_are_preserved_in_answer_and_separate_inequalities():
    a = analysis(case("646081"))
    p = plan(case("646081"))
    assert a.family_parameters == ("k", "n")
    assert r"2 \pi n" in p.answer and r"k,n\in" in p.answer
    second = BeautifulSoup(p.solution_html, "html.parser").select("li")[1]
    formulas = [n["data-inline-latex"] for n in second.select("[data-inline-latex]")]
    assert any(r"n\in" in f for f in formulas) and any(r"k\in" in f for f in formulas)
    assert (
        names(r'<span data-inline-latex="x=\frac{\pi}{6}+3\pi n"></span>', a.series)
        == ()
    )


def test_original_sine_cosine_domain_is_transformed_only_with_the_double_angle_proof():
    a = analysis(case("677685"))
    p = plan(case("677685"))
    assert a.homogeneous.source_poles and a.scale == 2
    assert a.series == ((-sp.Rational(1, 8), sp.Rational(1, 2)),)
    assert a.selected == rational(EXPECTED["677685"][1])
    assert "arctan" not in p.answer and "двойного угла" in p.solution_html


def test_high_angle_families_exclude_the_index_class_and_ignore_the_wrong_saved_header():
    a = analysis(case("695735"))
    p = plan(case("695735"))
    assert a.scale == sp.Rational(1, 2)
    assert [(f.parameter, f.modulus, f.excluded) for f in a.restricted_families] == [
        ("n", 1, ()),
        ("k", 9, (4,)),
    ]
    assert (
        r"\setminus\{9 p + 4\mid p\in\mathbb Z\}" in p.answer and "10" not in p.answer
    )
    assert sp.Rational(10, 9) not in select(a.series, (0, 2, True, False))[0]
    assert abs(complex(ORIGINAL["695735"].subs(X, 10 * sp.pi / 9).evalf(40))) > 1e-4
    assert all(
        not f.accepts(k)
        for f in a.restricted_families
        if f.parameter == "k"
        for k in (-5, 4, 13)
    )
    assert "ne q" not in p.solution_html


@pytest.mark.parametrize("formula", (r"\tanh x=0", r"\cotangent x=0", r"\tanother x=0"))
def test_standard_aliases_never_repair_unknown_function_names(formula):
    with pytest.raises(UnsupportedCondition):
        parse_equation(formula)


@pytest.mark.parametrize(
    "formula",
    (
        r"\cos 3x\sin\frac{x}{2}\cos\frac{9x}{2}/\cos 2x=0",
        r"\tg 2x+\frac{1}{\sin x}=\ctg x+\frac{1}{\sin 5x}+1",
        r"\tg 2x+\frac{1}{\sin x}=\ctg x+\frac{1}{\sin 5x+1}",
        r"\tg 13x+\frac{1}{\sin x}=\ctg x+\frac{1}{\sin 5x}",
    ),
)
def test_high_angle_quotients_fail_closed_without_the_domain_and_factor_certificates(
    formula,
):
    from solution_runner.pipelines.equations.exam_trigonometric_angle_quotients import (
        compile_product,
    )

    values, atoms, denominators = parse_equation(formula)
    with pytest.raises(UnsupportedCondition):
        compile_product(values, atoms, denominators, ())


def test_parent_inverse_sine_and_mixed_letters_remain_consistent_through_the_solution():
    p = plan(case("633751"))
    assert r"\arccos" not in p.solution_html and r"\arcsin" in p.solution_html
    p = plan(case("646081"))
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(p.solution_html, "html.parser").select(
            "[data-inline-latex]"
        )
    ]
    assert any(r"2 \pi n + \frac{5 \pi}{6}" in text for text in formulas)
    assert not any(text.startswith(r"x=2 \pi k + \frac{5 \pi}{6}") for text in formulas)
    p = plan(case("668795"))
    assert (
        "Знаменатели равны" in p.solution_html
        and "Объединим полученные серии" in p.solution_html
    )
