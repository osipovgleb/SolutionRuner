"""Original domains and independent complete root sets for exam logarithms."""

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
from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_logarithmic import analyze
from solution_runner.pipelines.equations.exam_logarithmic_input import (
    read,
    read_equation,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_14_logarithmic.json").read_text()
)
CASES = DATA["cases"]
EXPECTED = {
    "514082": ((-2, 1), (-2,)),
    "517739": ((-2, 16), (-2,)),
    "517746": ((-3, 27), (-3,)),
    "517747": ((-1, 3), (-1,)),
    "681754": ((-2, 4), (-2,)),
    "514623": ((2, 2 * sp.sqrt(2)), (2,)),
    "514637": ((3, 9), (9,)),
    "518113": ((2 * sp.sqrt(2), 4 * sp.sqrt(2)), (4 * sp.sqrt(2),)),
    "502053": (
        (-sp.sqrt(2), -sp.Rational(1, 2), sp.Rational(1, 2), sp.sqrt(2)),
        (-sp.Rational(1, 2), sp.Rational(1, 2)),
    ),
    "510741": ((-2 * sp.sqrt(3), -1, 1, 2 * sp.sqrt(3)), (-1, 1)),
    "510749": (
        (-sp.sqrt(7), -sp.sqrt(3), sp.sqrt(3), sp.sqrt(7)),
        (-sp.sqrt(3), sp.sqrt(3), sp.sqrt(7)),
    ),
    "511371": ((-2, 0, 2), (0,)),
    "525377": ((-1, 2), (-1,)),
}
L = sp.log
ORIGINAL = {
    "514082": L(2 - X) / L(5) - L(X**4) / L(25),
    "517739": L(X**2 - 14 * X) / L(2) - 5,
    "517746": L(X**2 - 24 * X) / L(3) - 4,
    "517747": L(X**2 - 2 * X) / L(3) - 1,
    "681754": L(X**2 - 2 * X) / L(2) - 3,
    "514623": 6 * (L(X) / L(8)) ** 2 - 5 * L(X) / L(8) + 1,
    "514637": 2 * (L(X) / L(9)) ** 2 - 3 * L(X) / L(9) + 1,
    "518113": (L(X**2) / L(2)) ** 2 - 16 * L(2 * X) / L(2) + 31,
    "502053": 1 + L(9 * X**2 + 5) / L(2) - L(sp.sqrt(8 * X**4 + 14)) / L(sp.sqrt(2)),
    "510741": L(3 * X**4 + 42) / L(3) - 1 - L(sp.sqrt(13 * X**2 + 2)) / L(sp.sqrt(3)),
    "510749": 1 + L(X**4 + 25) / L(3) - L(sp.sqrt(30 * X**2 + 12)) / L(sp.sqrt(3)),
    "511371": L(20 * X**2 + 8) / L(2) - L(sp.sqrt(10 * X**4 + 16)) / L(sp.sqrt(2)) + 1,
    "525377": L(X + 2) / L(7) - L(X**4) / L(49),
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


def analysis(c, context=None):
    _, formula, interval, bounds = read(context or c["context"])
    return analyze(formula, interval, bounds, parent(c))


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
def test_five_profiles_share_one_rule_with_exact_catalogue_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-logarithmic-interval"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.category_key,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], "14", 3, g["order"])


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_all_and_selected_roots_satisfy_independently_written_original_equations(c):
    a = analysis(c)
    assert (a.selection.roots, a.selection.selected) == EXPECTED[c["task"]]
    for r in a.selection.roots:
        for atom in a.atoms:
            assert sp.simplify(atom.argument.subs(X, r)).is_positive
        assert (
            sp.simplify(sp.expand_log(ORIGINAL[c["task"]].subs(X, r), force=True)) == 0
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_answers_and_replay_are_independent_of_saved_answers_and_solutions(c):
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
def test_parent_numbers_do_not_supply_child_calculations(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    for span in soup.select("[data-inline-latex]"):
        span["data-inline-latex"] = re.sub(r"\d+", "997", span["data-inline-latex"])
    p = plan(c)
    other = plan(c, prototype=str(soup))
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_empty_parent_unknown_instructions_and_assets_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype="")
    context = deepcopy(c["context"])
    context["normalized_content"]["assets"] = [{"asset_key": "unknown"}]
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = s["html"].replace("Ре­ши­те", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{1}(x)=0",
        r"\log_{0}(x)=0",
        r"\log_{-2}(x)=0",
        r"\log_x (x)=1",
        r"\log_2 (x)=1+x",
        r"\log_2 (x)=1+x^{-1}",
        r"\log_2 (x)=1+z",
        r"\log_2^3(x)=0",
        r"\log_2 (x)=0=1",
        r"\log_2 (x)=\sin(x)",
        r"\log_2 (x)=0; x>0",
    ],
)
def test_complete_logarithm_grammar_rejects_unknown_or_undefined_input(formula):
    with pytest.raises(UnsupportedCondition):
        read_equation(formula)


def test_squared_base_keeps_negative_roots_and_rejects_a_zero_argument():
    c, context = changed("514082", r"(2-x)", r"(x)")
    a = analysis(c, context)
    assert set(a.candidates) == {0, 1} and a.selection.roots == (1,)
    p = plan(case("514082"))
    assert "знак x не ограничивается" in p.solution_html
    assert -2 in analysis(case("514082")).selection.roots


def test_square_root_log_argument_keeps_its_strict_original_domain():
    c, context = changed(
        "502053",
        r"1+\log_{2}(9x^{2}+5)=\log_{\sqrt{2}}\sqrt{8x^{4}+14}.",
        r"1+\log_{2}(x^{2})=\log_{\sqrt{2}}\sqrt{2x^{4}}.",
    )
    a = analysis(c, context)
    assert set(a.candidates) == {-1, 0, 1} and a.selection.roots == (-1, 1)
    assert "при любом действительном" not in plan(c, context).solution_html


@pytest.mark.parametrize(
    "formula,roots",
    [
        (r"\log_8^{2}x+\log_8 x=0", (sp.Rational(1, 8), 1)),
        (r"\log_8^{2}x+1=0", ()),
    ],
)
def test_logarithm_substitution_keeps_nonpositive_levels_and_empty_root_sets(
    formula, roots
):
    c, context = changed("514623", r"6\log_8^{2} x-5\log_8 x+1=0", formula)
    assert analysis(c, context).selection.roots == roots
    plan(c, context)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("514082", r"\log_{(25)}", r"\log_{(125)}"),
        ("514623", r"\log_8^{2} x-5\log_8 x", r"\log_8^{2} (x^{2})-5\log_8 (x^{2})"),
        ("514623", r"\log_8 x", r"\log_9 x"),
        ("502053", r"\log_{\sqrt{2}}", r"\log_{\sqrt{3}}"),
        ("517739", r"\log_2 (x^{2}-14x)=5", r"\log_2 (x^{2}-14x)=\frac{1}{2}"),
    ],
)
def test_unreviewed_base_or_substitution_relations_fail_closed(task, old, new):
    c, context = changed(task, old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


def test_the_close_algebraic_upper_endpoint_excludes_two_exactly():
    a = analysis(case("511371"))
    assert a.selection.bounds[1] == sp.sqrt(323) / 9
    assert a.selection.selected == (0,)
    plan(case("511371"))


@pytest.mark.parametrize(
    "interval,selected",
    [(r"[2;2]", (2,)), (r"(2;3]", (2 * sp.sqrt(2),)), (r"[3;4]", ())],
)
def test_open_closed_and_singleton_intervals(interval, selected):
    c, context = changed("514623", r"[2;2{,}5]", interval)
    assert analysis(c, context).selection.selected == selected
    plan(c, context)


def test_parent_substitution_stays_before_selection_for_all_children():
    for c in CASES:
        if c["group"] != "514623":
            continue
        html = plan(c).solution_html
        assert (
            html.index("Положим")
            < html.index("Вернёмся к исходной переменной")
            < html.index("Отберём корни")
        )
