"""Shared affine graphs, inspected lattice points and the parents' proof methods."""

import hashlib
import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan, replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import linear_models as model
from solution_runner.pipelines.function_graphs import linear_svg

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_linear.json").read_text()
)
CASES = DATA["cases"]


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
def test_five_groups_register_one_affine_graph_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.content_rule_key == group["rule"] == "linear-function-graph"
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert (
        profile.category_key == "12" and profile.existing_solution_policy == "rewrite"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_sources_replay_without_saved_answers_or_solution_numbers(case):
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
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    assert plan(case, context).answer == p.answer
    updated = replay(original, p.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    original_condition = next(
        s for s in original["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert original_condition == next(
        s for s in updated["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in p.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_raw_svg_geometry_and_exact_affine_equations_agree(case):
    data = data_for(case)
    digest = hashlib.sha256(data).hexdigest()
    assert digest == case["condition_sha256"]
    entry = model.registry()[digest]
    assert entry["grid_unit"] == [1, 1]
    assert linear_svg.read(data) == entry["lines"]
    a = model.calculate(case["context"], data, "image/svg+xml")
    for one in a.lines:
        assert all(one.value(x) == y for x, y in one.points)
    if a.kind == "value":
        assert a.result == a.lines[0].value(a.target)
    elif a.kind == "argument":
        assert a.lines[0].value(a.result) == a.target
    else:
        x, y = a.intersection
        assert all(one.value(x) == y for one in a.lines)
        assert a.result == (x if a.kind == "intersection_x" else y)
    with pytest.raises(ContentPlanError, match="inspected registration"):
        plan(case, data=data + b" ")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mode", ["leading", "trailing", "extra_math", "extra_image", "wrong_image"]
)
def test_full_questions_and_figure_identity_cannot_ignore_changes(case, mode):
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
def test_foreign_solution_figures_and_rasters_fail_closed(case):
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] += '<img src="/assets/foreign"/>'
    with pytest.raises(ContentPlanError, match="only the original"):
        plan(case, context)
    with pytest.raises(ContentPlanError, match="inspected SVG"):
        plan(case, mime="image/png")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_methods_are_selected_by_the_question_and_use_actual_graph_colors(case):
    p = plan(case)
    updated = replay(case["context"], p.transformations)
    html = next(
        s["html"]
        for s in updated["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    if case["group"] == "508895":
        methods = BeautifulSoup(html, "html.parser").select(
            'section[data-content-kind="solution"]'
        )
        assert len(methods) == 2
        assert "любом участке" in methods[0].get_text()
        assert "свободный член" in methods[1].get_text()
    elif case["group"] == "508903":
        assert "решим систему" in html and r"\begin{cases}" in html
    else:
        assert "тёмно-синим" in html and "бирюзовым" in html
        assert "оранжевым" not in html
        assert "приращений" in html and "тангенс" in html
        assert ("найти ординату" in html) == (case["group"] != "509197")


def test_wrong_saved_positive_argument_is_replaced_with_the_requested_negative_one():
    case = case_for("508898")
    updated = replay(case["context"], plan(case).transformations)
    html = next(
        s["html"]
        for s in updated["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert "f(-10)" in html and "f(10)" not in html


def test_requested_marked_value_uses_the_other_reference_point_without_zero_denominator():
    case = case_for("508895")
    p = plan(case, changed(case, "f(-5)", "f(-1)"))
    assert p.answer == "-3"
    case = case_for("508903")
    assert plan(case, changed(case, "f(x)=-13{,}5", "f(x)=4")).answer == "3"


def test_constant_inverse_parallel_lines_and_vertical_graphs_are_not_unique_functions():
    constant = model.Line(
        "#143B8F", ((Fraction(0), Fraction(1)), (Fraction(1), Fraction(1)))
    )
    assert model.analyze("value", Fraction(5), (constant,)).result == 1
    with pytest.raises(ContentPlanError, match="no unique inverse"):
        model.analyze("argument", Fraction(1), (constant,))
    with pytest.raises(ContentPlanError, match="nonparallel"):
        model.analyze("intersection_x", None, (constant, constant))
    vertical = model.Line(
        "#143B8F", ((Fraction(0), Fraction(1)), (Fraction(0), Fraction(2)))
    )
    with pytest.raises(ContentPlanError, match="vertical"):
        model.analyze("value", Fraction(1), (vertical,))


def test_audited_point_data_must_agree_with_independently_read_geometry(monkeypatch):
    case = case_for("508895")
    original = model.registry()
    original[case["condition_sha256"]]["lines"][0]["points"][0][0] += 1
    monkeypatch.setattr(model, "registry", lambda: original)
    with pytest.raises(ContentPlanError, match="disagrees"):
        plan(case)
