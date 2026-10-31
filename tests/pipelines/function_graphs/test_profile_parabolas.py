"""Every quadratic source, exact graph data and all parent solution methods."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan, replay

from solution_runner.pipelines.calculus.common import X
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import parabola_models as model
from solution_runner.pipelines.function_graphs import parabola_svg
from solution_runner.pipelines.function_graphs.linear_svg import NS, snap
from solution_runner.pipelines.function_graphs.parabola_questions import Question
from solution_runner.pipelines.function_graphs.parabola_vertex_proof import recover

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_parabolas.json").read_text()
)
CASES = DATA["cases"]
METHODS = {
    "508911": 1,
    "508919": 2,
    "508927": 1,
    "508935": 2,
    "508943": 1,
    "509253": 1,
    "509262": 2,
    "564646": 1,
}


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def data_for(case):
    return (ROOT / case["condition_file"]).read_bytes()


def changed(case, old, new):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_eight_groups_register_one_quadratic_graph_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.content_rule_key == group["rule"] == "quadratic-function-graph"
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert (
        profile.category_key == "12" and profile.existing_solution_policy == "rewrite"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_replays_without_saved_answers_or_solution_numbers(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    p = plan(case, context)
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert parse_rational(p.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    assert context == original
    for section in context["normalized_content"]["sections"]:
        if section["key"] in {"answer", "solution"}:
            section["html"] = "<p>999999999</p>"
    assert plan(case, context).answer == p.answer
    updated = replay(original, p.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    assert next(
        s for s in updated["normalized_content"]["sections"] if s["key"] == "condition"
    ) == next(
        s for s in original["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in p.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_inspected_curve_and_marked_points_match_the_exact_polynomial(case):
    data = data_for(case)
    assert hashlib.sha256(data).hexdigest() == case["condition_sha256"]
    entry = model.registry()[case["condition_sha256"]]
    root, axes = parabola_svg.read(data, entry)
    a = model.calculate(case["context"], data, "image/svg+xml")
    assert all(
        a.expression.subs(X, p[0]) == p[1]
        for p in a.curve["points"] + a.curve["marked_points"]
    )
    if a.question.kind == "value":
        assert a.result == a.expression.subs(X, a.question.target)
        if a.question.whole:
            assert all(
                c.is_Integer is True for c in sp.Poly(a.expression, X).all_coeffs()
            )
    else:
        assert all(
            a.question.given.subs(X, r) == a.expression.subs(X, r) for r in a.roots
        )
        assert a.root != a.visible_a and set(a.roots) == {a.root, a.visible_a}
        assert a.result == (
            a.root
            if a.question.kind == "intersection_x"
            else a.expression.subs(X, a.root)
        )
        xm, ym, sx, sy = axes
        markers = {
            (snap(float(n.get("cx")), xm, sx), snap(float(n.get("cy")), ym, sy))
            for n in root.iter(NS + "circle")
        }
        assert (a.visible_a, a.expression.subs(X, a.visible_a)) in markers
    with pytest.raises(ContentPlanError, match="inspected registration"):
        plan(case, data=data + b" ")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mode", ["leading", "trailing", "extra_math", "extra_image", "wrong_image"]
)
def test_complete_questions_and_figure_identity_fail_closed(case, mode):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mode in {"leading", "trailing"}:
        extra = "<p>Ответ округлите до целого числа.</p>"
        condition["html"] = (
            extra + condition["html"]
            if mode == "leading"
            else condition["html"] + extra
        )
    elif mode == "extra_math":
        condition["html"] += '<span data-inline-latex="x=0"></span>'
    elif mode == "extra_image":
        condition["html"] += '<img src="/assets/foreign"/>'
    else:
        soup = BeautifulSoup(condition["html"], "html.parser")
        soup.img["src"] = "/assets/foreign"
        condition["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_methods_stay_in_parent_order_and_fractional_vertices_are_explained(case):
    a = model.calculate(case["context"], data_for(case), "image/svg+xml")
    p = plan(case)
    html = next(
        s["html"]
        for s in replay(case["context"], p.transformations)["normalized_content"][
            "sections"
        ]
        if s["key"] == "solution"
    )
    methods = BeautifulSoup(html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert max(1, len(methods)) == METHODS[case["group"]]
    if METHODS[case["group"]] == 2:
        assert "вершин" in methods[0].get_text()
        assert "Исключим вторую неизвестную" in methods[1].get_text()
    if case["group"] == "508911":
        assert "Выразим свободный член" in html and "подставим во второе" in html
    if case["group"] in {"508943", "564646"}:
        assert "вершин" in html
    if a.question.kind != "value":
        assert "точка A" in html and "второй корень" in html
        assert "оранжевым" not in html
    if (METHODS[case["group"]] == 2 or a.question.whole) and not a.curve.get("vertex"):
        assert "не отмечена в узле" in html
        scale, h, k, _ = recover(a)
        assert sp.expand(scale * (X - h) ** 2 + k) == a.expression


@pytest.mark.parametrize(
    "task,root,visible",
    [("509253", 7, 2), ("509254", -12, -1), ("509255", -6, -1), ("509256", 5, 1)],
)
def test_B_is_the_other_intersection_instead_of_always_the_larger_root(
    task, root, visible
):
    case = case_for(task)
    a = model.calculate(case["context"], data_for(case), "image/svg+xml")
    assert a.root == root and a.visible_a == visible


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("508911", "2x^{2}", "3x^{2}", "stated coefficient"),
        ("508919", "-4x+c", "-5x+c", "stated coefficient"),
        ("508927", "bx-6", "bx-7", "stated coefficient"),
        ("508943", "— целые", "— положительные", "complete quadratic"),
        ("509253", "4x^{2}", "5x^{2}", "exactly one pictured"),
        (
            "509253",
            'точки <var data-math-identifier="B">B</var>',
            'точки <var data-math-identifier="A">A</var>',
            "complete quadratic",
        ),
    ],
)
def test_changed_coefficients_and_unread_constraints_do_not_reuse_a_wrong_answer(
    task, old, new, error
):
    case = case_for(task)
    with pytest.raises((ContentPlanError, ValueError), match=error):
        plan(case, changed(case, old, new))


def test_collinear_points_do_not_define_a_parabola_and_integer_constraints_are_enforced(
    monkeypatch,
):
    with pytest.raises(ContentPlanError, match="nondegenerate"):
        model.fit([[0, 0], [1, 1], [2, 2]])
    case = case_for("508943")
    entry = deepcopy(model.registry()[case["condition_sha256"]])
    entry["curves"][0]["points"] = [[0, 0], [1, 0], [2, 1]]
    entry["curves"][0]["marked_points"] = []
    monkeypatch.setattr(
        parabola_svg, "read", lambda data, entry: (ET.Element("svg"), ())
    )
    with pytest.raises(ContentPlanError, match="integer coefficients"):
        model.analyze(
            Question("value", {}, True, sp.Integer(1)), entry, b"inspected test image"
        )


def test_intersection_label_and_foreign_solution_figures_cannot_be_ignored(monkeypatch):
    case = case_for("509253")
    reg = model.registry()
    reg[case["condition_sha256"]]["visible_intersection_label"] = "B"
    monkeypatch.setattr(model, "registry", lambda: reg)
    with pytest.raises(ContentPlanError, match="visible label A"):
        plan(case)
    case = case_for("508911")
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] += '<img src="/assets/foreign"/>'
    with pytest.raises(ContentPlanError, match="only the original"):
        plan(case, context)
