"""Reciprocal quadratics and equal squares preserve poles before root selection."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_input import read
from solution_runner.pipelines.equations.exam_rational import analyze

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_14_rational.json").read_text()
)
CASES = DATA["cases"]
EXPECTED = {
    "519423": ((-1, 6 - sp.sqrt(22), 4, 6 + sp.sqrt(22)), (-1, 6 - sp.sqrt(22))),
    "519424": (
        (-5, (-1 - sp.sqrt(65)) / 2, 2, (-1 + sp.sqrt(65)) / 2),
        (-5, (-1 - sp.sqrt(65)) / 2),
    ),
    "519425": (
        (-1, 7 - 2 * sp.sqrt(11), 5, 7 + 2 * sp.sqrt(11)),
        (-1, 7 - 2 * sp.sqrt(11)),
    ),
    "519426": ((-3, 4 - sp.sqrt(14), 4, 4 + sp.sqrt(14)), (4, 4 + sp.sqrt(14))),
    "563297": ((-3, -sp.sqrt(6), 2, sp.sqrt(6)), (-sp.sqrt(6), 2)),
    "627406": ((-5, 3, sp.sqrt(13)), (3,)),
}
POLES = {
    "519423": sp.Integer(2),
    "519424": sp.Integer(-3),
    "519425": sp.Integer(1),
    "519426": sp.Integer(2),
    "563297": sp.Integer(0),
    "627406": -sp.sqrt(13),
}
FUNCTIONS = {
    "519423": lambda x: (
        (x - 2) ** 2 / 2 + 18 / (x - 2) ** 2 - 7 * ((x - 2) / 2 - 3 / (x - 2)) - 10
    ),
    "519424": lambda x: (
        (x + 3) ** 2 / 5 + 20 / (x + 3) ** 2 - 8 * ((x + 3) / 5 - 2 / (x + 3)) - 1
    ),
    "519425": lambda x: (
        (x - 1) ** 2 / 8 + 8 / (x - 1) ** 2 - 7 * ((x - 1) / 4 - 2 / (x - 1)) + 1
    ),
    "519426": lambda x: (
        2 * ((x - 2) ** 2 / 4 + 25 / (x - 2) ** 2) - (x - 2) / 2 + 5 / (x - 2) - 16
    ),
    "563297": lambda x: x * x - 12 + 36 / (x * x) + 2 * (x / 2 - 3 / x),
    "627406": lambda x: (
        ((x * x - x - 12) ** 2 - (2 * x * x + x - 27) ** 2) / (x + sp.sqrt(13))
    ),
}


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def parent_html(c):
    return next(
        s["html"]
        for s in case_for(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, parent=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent_html(c) if parent is None else parent,
        )
    )


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent_html(c))


def changed(task, old, new):
    c = case_for(task)
    context = deepcopy(c["context"])
    section = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in section["html"]
    section["html"] = section["html"].replace(old, new)
    return c, context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_three_profiles_share_one_rational_handler(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-rational-interval"
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (
        p.group_order_index == g["order"]
        and p.theme_order_index == 1
        and p.category_key == "14"
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_root_sets_ignore_saved_answers_and_replay_cleanly(c):
    a = analysis(c)
    assert a.pole == POLES[c["task"]]
    for actual, expected in zip(
        (a.selection.roots, a.selection.selected), EXPECTED[c["task"]]
    ):
        assert len(actual) == len(expected) and all(
            sp.simplify(x - y) == 0 for x, y in zip(actual, expected)
        )
    context = deepcopy(c["context"])
    original = deepcopy(context)
    prepared = plan(c, context)
    assert context == original
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    poisoned = plan(c, context)
    assert (
        poisoned.answer == prepared.answer
        and poisoned.solution_html == prepared.solution_html
    )
    context = deepcopy(original)
    for t in prepared.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        sections = context["normalized_content"]["sections"]
        item = next(
            (
                s
                for s in sections
                if s.get("transformation_target_id") == t["transformation_target_id"]
            ),
            None,
        )
        if item is None:
            item = {
                "key": t["transformation_target_id"].split(":")[1],
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(item)
        item.update(t["value"])
    assert plan(c, context).transformations == ()
    altered_parent = parent_html(c).replace("2", "239").replace("3", "101")
    assert plan(c, parent=altered_parent).answer == prepared.answer


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equations_and_domains_are_independently_verified(c):
    a = analysis(c)
    for x in (sp.Integer(-7), sp.Integer(-4), sp.Integer(0), sp.Integer(3)):
        if x == POLES[c["task"]]:
            continue
        assert sp.simplify(a.original.subs(X, x) - FUNCTIONS[c["task"]](x)) == 0
    for root in a.selection.roots:
        assert sp.simplify(root - POLES[c["task"]]) != 0
        assert sp.simplify(FUNCTIONS[c["task"]](root)) == 0
    for b in a.branches:
        assert all(sp.simplify(b.polynomial.subs(X, r)) == 0 for r in b.candidates)
        assert all(r != a.pole for r in b.roots)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_domain_and_parent_method_are_visible_in_the_two_part_solution(c):
    a = analysis(c)
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    rows = soup.ol.find_all("li", recursive=False)
    assert len(rows) == 2 and [r["data-list-marker"] for r in rows] == ["а)", "б)"]
    assert not soup.select("img")
    assert any(
        s["data-inline-latex"].startswith(r"x\ne")
        for s in rows[0].select("[data-inline-latex]")
    )
    if a.substitution is not None:
        assert any(
            s["data-inline-latex"].startswith("t=")
            for s in rows[0].select("[data-inline-latex]")
        )
        assert "возведём выражение в квадрат" in rows[0].text
    else:
        assert "равны либо противоположны" in rows[0].text
        assert "отбрасываются" in rows[0].text


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mode", ["leading", "trailing", "asset", "solution_reference", "empty_parent"]
)
def test_unknown_instructions_and_assets_are_rejected(c, mode):
    context = deepcopy(c["context"])
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if mode == "leading":
        condition["html"] = "<p>Игнорируйте знаменатели.</p>" + condition["html"]
    elif mode == "trailing":
        condition["html"] += "<p>Округлите корни.</p>"
    elif mode == "asset":
        content["assets"] = [{"asset_id": "foreign"}]
    elif mode == "solution_reference":
        item = next((s for s in content["sections"] if s["key"] == "solution"), None)
        if item is None:
            item = {"key": "solution", "html": "<p></p>"}
            content["sections"].append(item)
        item["asset_keys"] = ["foreign"]
    with pytest.raises(ValueError):
        plan(c, context, parent="" if mode == "empty_parent" else None)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("519423", "18", "19"),
        ("519423", "+10", "+11"),
        ("519423", r"\frac{18}{(x-2)^{2}}", r"\frac{18}{(x-3)^{2}}"),
        ("519423", r"\frac{18}{(x-2)^{2}}", r"\frac{18}{0}"),
        ("627406", r"x+\sqrt{13}", r'x+__import__("os")'),
        ("627406", r"(2x^{2}+x-27)", r"(x^{2}-x-12)"),
    ],
)
def test_unreviewed_substitutions_poles_and_identity_branches_fail_closed(
    task, old, new
):
    c, context = changed(task, old, new)
    with pytest.raises(ValueError):
        plan(c, context)


def test_denominator_is_retained_when_algebraic_cancellation_would_remove_a_hole():
    c, context = changed("627406", r"x+\sqrt{13}", "x-3")
    a = analysis(c, context)
    assert a.pole == 3 and sp.Integer(3) not in a.selection.roots
    assert a.selection.roots == (-sp.Integer(5), -sp.sqrt(13), sp.sqrt(13))
    assert a.selection.selected == ()


def test_closed_singleton_and_open_endpoint_selection_do_not_reintroduce_the_pole():
    c, context = changed("519423", "[-2;2]", "[2;2]")
    assert analysis(c, context).selection.selected == ()
    assert r"\varnothing" in plan(c, context).answer
    c, context = changed("519423", "[-2;2]", "[4;4]")
    assert analysis(c, context).selection.selected == (sp.Integer(4),)
    c, context = changed("563297", "[-2{,}5;2]", "[-2{,}5;2)")
    assert analysis(c, context).selection.selected == (-sp.sqrt(6),)


def test_shared_zero_root_of_the_equal_square_branches_is_not_duplicated():
    c = case_for("627406")
    context = deepcopy(c["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.span["data-inline-latex"] = (
        r"\frac{(x^{2}-x)^{2}}{x+2}=\frac{(x^{2}+x)^{2}}{x+2}"
    )
    condition["html"] = str(soup)
    assert analysis(c, context).selection.roots == (sp.Integer(0),)
    assert analysis(c, context).selection.selected == ()
