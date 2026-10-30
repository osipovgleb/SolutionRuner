"""Every integral sample, preserved parent methods, and mathematical refusals."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import graph_integrals as graph
from solution_runner.pipelines.calculus.common import X
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_integrals.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def solution(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_integral_groups_share_one_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == group["rule"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_answers_are_computed_and_plans_are_local_and_idempotent(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    first = plan(case, context)
    assert parse_rational(first.answer) == parse_rational(
        BeautifulSoup(expected, "html.parser").get_text()
    )
    assert context == original
    assert all(
        t["transformation_target_id"].startswith(
            ("section:answer", "section:solution", "asset:")
        )
        for t in first.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert plan(case, context).answer == first.answer
    context = deepcopy(original)
    _apply_local(context, first.transformations)
    assert plan(case, context).transformations == ()
    assert len(BeautifulSoup(solution(first), "html.parser").find_all("img")) == (
        1 if case["group"] in ["323078", "500890"] else 0
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_changed_source_assets_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Часть фигуры слева не учитывайте.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"another shading")


@pytest.mark.parametrize("task", ["323078", "323183", "323185", "323275"])
def test_piecewise_primitive_is_continuous_and_has_the_correct_one_sided_derivatives(
    task,
):
    _, _, m = graph.calculate(sample(task)["context"])
    right = m.right_primitive + m.adjustment
    assert right.subs(X, m.join) == m.height * m.join
    quotient = sp.cancel((right - right.subs(X, m.join)) / (X - m.join))
    assert sp.limit(quotient, X, m.join, dir="+") == m.height
    assert sp.diff(right, X).subs(X, m.join) == m.height
    assert sp.expand(right - m.height * X - m.slope * (X - m.join) ** 2 / 2) == 0
    assert m.result == sp.integrate(m.height, (X, m.lower, m.join)) + sp.integrate(
        m.right, (X, m.join, m.upper)
    )
    html = solution(plan(sample(task), sample(task)["context"]))
    assert "Аналитическое решение" in html and "Односторонние производные" in html
    assert "Непрерывности недостаточно" in html and "общую касательную" in html


@pytest.mark.parametrize("task", ["323079", "323283", "323373", "323375"])
def test_all_four_parent_methods_and_the_symmetry_note_are_preserved(task):
    case = sample(task)
    html = solution(plan(case, case["context"]))
    for text in [
        "разности значений",
        "полный куб",
        "формулы сокращённого умножения",
        "Перенесём начало отсчёта",
        "Примечание.",
        "чётная",
    ]:
        assert text in html
    _, _, m = graph.calculate(case["context"])
    assert sp.integrate(m.function, (X, m.lower, m.upper)) == m.result
    assert m.vertex_height > 0 and m.curvature > 0


def test_free_constant_does_not_change_area_or_graph_compatibility():
    case = sample("323079")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    formula = next(
        s
        for s in soup.select("[data-inline-latex]")
        if s["data-inline-latex"].startswith("F(x)=")
    )
    formula["data-inline-latex"] += "+17"
    condition["html"] = str(soup)
    assert plan(case, context).answer == "6"


@pytest.mark.parametrize("task", ["323080", "323383", "323475", "323477"])
def test_cap_area_uses_the_shift_and_exact_rational_limits(task):
    case = sample(task)
    _, _, m = graph.calculate(case["context"])
    assert m.function.subs(X, m.lower) == m.function.subs(X, m.upper) == 0
    assert m.curvature < 0 and m.function.subs(X, m.center) > 0
    assert sp.integrate(m.function, (X, m.lower, m.upper)) == m.result
    html = solution(plan(case, case["context"]))
    assert "Полученная функция чётная" in html
    assert "полный куб" not in html


def test_primitive_cannot_silently_change_the_integrand_or_shaded_interval():
    data, question, _ = graph.calculate(sample("323079")["context"])
    with pytest.raises(ValueError, match="derivative does not match"):
        graph.area_model(replace(question, primitive=question.primitive + X), data[5])
    entry = deepcopy(data[5])
    entry["area_span"] = [-11, -8]
    with pytest.raises(ValueError, match="symmetric"):
        graph.area_model(question, entry)
    entry = deepcopy(data[5])
    entry["area_svg_span"] = [10000, 10010]
    with pytest.raises(ValueError, match="graph branch"):
        graph.area_model(question, entry)


def test_ray_labels_and_source_shading_are_checked_before_planning():
    data, question, _ = graph.calculate(sample("323078")["context"])
    entry = deepcopy(data[5])
    entry["plateau_height"] = 3
    with pytest.raises(ValueError, match="labelled grid"):
        graph.piecewise_model(question, entry)
    with pytest.raises(ValueError, match="shading"):
        graph.piecewise_model(replace(question, lower=sp.Rational(1)), data[5])
    with pytest.raises(ValueError, match="trapezoid"):
        graph.piecewise_model(replace(question, upper=sp.Rational(9)), data[5])


def test_bibliographic_scans_are_removed_only_from_the_local_plan():
    case = sample("323078")
    original = deepcopy(case["context"])
    result = plan(case, case["context"])
    removed = [
        t["transformation_target_id"]
        for t in result.transformations
        if t["operation"] == "remove"
    ]
    assert removed == ["asset:image_3", "asset:image_4", "asset:image_5"]
    assert case["context"] == original
    assert "непрерывность" in solution(result).lower()
    assert "Контрольная работа" not in solution(result)
    context = deepcopy(original)
    context["normalized_content"]["assets"][-1]["asset_id"] = "unrelated"
    with pytest.raises(ValueError, match="unrelated"):
        plan(case, context)


def test_explicit_integral_preserves_triangle_then_rectangle_method():
    case = sample("500890")
    html = solution(plan(case, case["context"]))
    assert html.index("S_{\\mathrm{тр}}") < html.index("S_{\\mathrm{пр}}")
    assert "Аналитическое решение" not in html
    assert "4+8=12" in html
