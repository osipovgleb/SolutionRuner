"""Independent roots, sign rejection, continuous sets and every original method."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations import exam_nested_radical, exam_radical
from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_input import read, read_parts
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_14_radical.json").read_text()
)
CASES = DATA["cases"]
FINITE = [c for c in CASES if c["group"] != "507572"]
NESTED = [c for c in CASES if c["group"] == "507572"]
EXPECTED = {
    "521850": ((sp.Rational(1, 2),), (sp.Rational(1, 2),)),
    "520994": ((2, 5), (2,)),
    "519658": ((-2, 2), (2,)),
    "549170": ((0, (-3 + sp.sqrt(33)) / 2), (0, (-3 + sp.sqrt(33)) / 2)),
    "639112": (
        ((-1 - sp.sqrt(13)) / 2, (1 + sp.sqrt(17)) / 2),
        ((1 + sp.sqrt(17)) / 2,),
    ),
}
ORIGINAL = {
    "521850": (X**4 + 8 * X**3 + 2 * X**2 - 1, X**4 + 2 * X**2),
    "520994": (X - 1, (X + 1) / 3),
    "519658": (X**3 - 4 * X**2 - 10 * X + 29, 3 - X),
    "549170": (X**3 + 4 * X**2 + 9, X + 3),
    "639112": (X + 4, X**2 - 4),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def analyze(c, context=None):
    if c["group"] == "507572":
        _, formula, second = read_parts(context or c["context"])
        return exam_nested_radical.analyze(formula, second, parent(c))
    _, formula, interval, bounds = read(context or c["context"])
    return exam_radical.analyze(formula, interval, bounds, parent(c))


def changed(task, old, new):
    c = case(task)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in s["html"]
    s["html"] = s["html"].replace(old, new)
    return c, context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_profiles_have_exact_catalogue_positions(g):
    p = get_group_profile(g["key"])
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (p.category_key, p.theme_order_index, p.group_order_index) == (
        "14",
        2,
        g["order"],
    )
    assert p.content_rule_key == (
        "exam-nested-radical-interval"
        if g["key"] == "507572"
        else "exam-radical-interval"
    )


@pytest.mark.parametrize("c", FINITE, ids=lambda c: c["task"])
def test_exact_roots_and_signs_from_independently_written_original_equations(c):
    a = analyze(c)
    assert (a.selection.roots, a.selection.selected) == EXPECTED[c["task"]]
    p, b = ORIGINAL[c["task"]]
    for r in a.selection.roots:
        value = sp.simplify(p.subs(X, r))
        other = sp.simplify(b.subs(X, r))
        assert value.is_nonnegative
        if c["task"] == "521850":
            assert sp.simplify(value - other) == 0 and other.is_nonnegative
        else:
            assert other.is_nonnegative and sp.simplify(value - other**2) == 0
    assert a.selection.roots


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_context_is_unchanged_and_replay_is_empty(c):
    context = deepcopy(c["context"])
    before = deepcopy(context)
    p = plan(c, context)
    assert context == before and p.condition_html == next(
        s["html"]
        for s in before["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in context["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>INVALID 999999</p>"
    other = plan(c, context)
    assert other.answer == p.answer and other.solution_html == p.solution_html
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        s = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        s.update(t["value"])
    assert plan(c, context).transformations == ()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_numeric_values_do_not_supply_child_calculations(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    for span in soup.select("[data-inline-latex]"):
        span["data-inline-latex"] = re.sub(r"\d+", "997", span["data-inline-latex"])
    assert plan(c, prototype=str(soup)).answer == plan(c).answer


@pytest.mark.parametrize("c", NESTED, ids=lambda c: c["task"])
def test_continuous_solution_interval_is_not_reduced_to_finitely_many_roots(c):
    a = analyze(c)
    expected = {
        "507572": (4, (2 * sp.sqrt(3) + 1, 8, True, True)),
        "507577": (1, None),
        "511441": (9, (4 * sp.sqrt(7) - 1, 18, True, True)),
    }
    centre, selected = expected[c["task"]]
    assert a.centre == centre and a.selected == selected
    if a.points:
        assert a.points == (sp.Rational(3, 2), 2 * sp.sqrt(3) - 3) and a.membership == (
            True,
            False,
        )
    for i in range(13):
        y = a.coefficient * sp.Rational(i, 12)
        x = y * y + centre
        actual = sp.sqrt(x + a.coefficient * sp.sqrt(x - centre)) + sp.sqrt(
            x - a.coefficient * sp.sqrt(x - centre)
        )
        assert (sp.simplify(actual - a.coefficient) == 0) == (i <= 6)


def test_every_parent_method_stays_in_its_original_position():
    p = plan(case("520994")).solution_html
    assert (
        p.index("При отрицательной")
        < p.index("Отберём корни")
        < p.index("Примечание")
        < p.index("Приведём другое решение")
    )
    p = plan(case("639112")).solution_html
    assert (
        p.index("суммой")
        < p.index("Отберём корни")
        < p.index("Приведём другое решение")
        < p.index("Приведём еще одно решение")
        < p.index("квадратное относительно")
    )
    for c in NESTED:
        soup = BeautifulSoup(plan(c).solution_html, "html.parser")
        sections = soup.find_all("section", recursive=False)
        assert [s["data-solution-title"] for s in sections] == [
            "Решение",
            "Приведем другое решение.",
        ]
        assert (
            "неположительных" in sections[0].get_text()
            and "возведём их в квадрат" in sections[1].get_text()
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_empty_parent_and_assets_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype="")
    context = deepcopy(c["context"])
    context["normalized_content"]["assets"] = [{"asset_key": "unknown"}]
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("521850", "<sub>3</sub>", '<sub onclick="x">3</sub>'),
        ("521850", "<sub>3</sub>", "<sub>x</sub>"),
        ("519658", "Ука­жи­те все корни", "Ука­жи­те все положительные корни"),
        ("520994", r"x-3\sqrt{x-1}+1=0", r"x-3\sqrt{x-1}+1=0+x^{-1}"),
        ("520994", r"x-3\sqrt{x-1}+1=0", r"\sqrt{x-1}+\sqrt{x+1}=2"),
        ("507572", r"4\sqrt{x-4}", r"5\sqrt{x-4}"),
        ("507577", "числа 1,5 и", "числа 1,5, 1,7 и"),
        ("639112", r"\sqrt{x+4}=x^{2}-4", r"\sqrt{x+5}=x^{2}-4"),
    ],
)
def test_changed_method_unknown_instructions_or_poles_fail_closed(task, old, new):
    c, context = changed(task, old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


def test_squaring_extraneous_roots_are_rejected_before_interval_selection():
    assert set(analyze(case("519658")).candidates) == {-2, 2, 5}
    a = analyze(case("549170"))
    assert (-3 - sp.sqrt(33)) / 2 in a.candidates and (
        -3 - sp.sqrt(33)
    ) / 2 not in a.selection.roots
    a = analyze(case("639112"))
    assert len(a.candidates) == 4 and len(a.selection.roots) == 2


@pytest.mark.parametrize(
    "replacement,expected", [(r"[2;2]", (2,)), (r"(2;5]", (5,)), (r"[3;4]", ())]
)
def test_root_on_endpoint_obeys_the_requested_open_or_closed_boundary(
    replacement, expected
):
    c, context = changed("520994", r"[\sqrt{3};\sqrt{20}]", replacement)
    assert analyze(c, context).selection.selected == expected


@pytest.mark.parametrize(
    "replacement,expected",
    [
        (r"[0;4]", (4, 4, True, True)),
        (r"(0;4)", None),
        (r"[9;10]", None),
        (r"(4;8)", (4, 8, False, False)),
    ],
)
def test_continuous_intersection_handles_empty_singleton_and_open_sets(
    replacement, expected
):
    c, context = changed("507572", r"[2\sqrt{3}+1;10]", replacement)
    assert analyze(c, context).selected == expected
    plan(c, context)


@pytest.mark.parametrize(
    "equation,expected",
    [
        (r"x-\sqrt{x-1}-1=0", (1, 2)),
        (r"x+3\sqrt{x-1}-1=0", (1,)),
        (r"x+\sqrt{x-1}+1=0", ()),
    ],
)
def test_alternative_substitution_keeps_zero_and_rejects_negative_levels(
    equation, expected
):
    c, context = changed("520994", r"x-3\sqrt{x-1}+1=0", equation)
    assert analyze(c, context).selection.roots == expected
    plan(c, context)


@pytest.mark.parametrize(
    "equation,expected",
    [
        (r"\sqrt{x-1}=\sqrt{1-x}", (1,)),
        (r"\sqrt{x-2}=\sqrt{2x-3}", ()),
    ],
)
def test_equal_radicands_still_need_their_original_nonnegative_domain(
    equation, expected
):
    c, context = changed(
        "521850", r"\sqrt{x^{4}+8x^{3}+2x^{2}-1}=\sqrt{x^{4}+2x^{2}}", equation
    )
    assert analyze(c, context).selection.roots == expected
    plan(c, context)


def test_finite_rule_rejects_an_identity_with_infinite_solutions():
    c, context = changed("519658", r"\sqrt{x^{3}-4x^{2}-10x+29}=3-x", r"\sqrt{x^{2}}=x")
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


def test_symmetric_rule_does_not_drop_the_third_parent_method():
    c = case("639112")
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c).replace("еще одно", "неизвестное"))


def test_equal_radicals_keep_the_parents_cubic_inversion():
    p = plan(case("521850")).solution_html
    assert 'data-inline-latex="x^3=\\frac{1}{8}"' in p
    assert "строго возрастает" in p
