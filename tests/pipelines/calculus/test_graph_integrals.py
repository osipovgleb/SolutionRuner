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
def test_integral_groups_select_their_explicit_rule(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == (
        "calculus-raster-parabola-area"
        if group["key"] in ("323079", "323080")
        else (
            "calculus-raster-trapezoid-rays"
            if group["key"] in {"323078", "500890"}
            else group["rule"]
        )
    )
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
    assert (
        "Аналитическое решение" not in html and "Односторонние производные" not in html
    )
    assert "Непрерывности недостаточно" not in html
    assert "Это трапеция с основаниями" in html
    assert r"\int" not in html


@pytest.mark.parametrize("task", ["323079", "323283", "323373", "323375"])
def test_bowl_area_has_only_the_endpoint_method(task):
    case = sample(task)
    html = solution(plan(case, case["context"]))
    assert "разности значений" in html
    for text in [
        "полный куб",
        "формулы сокращённого умножения",
        "Перенесём",
        "Примечание.",
        "чётная",
    ]:
        assert text not in html
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
def test_cap_area_uses_endpoint_values_and_exact_rational_limits(task):
    case = sample(task)
    _, _, m = graph.calculate(case["context"])
    assert m.function.subs(X, m.lower) == m.function.subs(X, m.upper) == 0
    assert m.curvature < 0 and m.function.subs(X, m.center) > 0
    assert sp.integrate(m.function, (X, m.lower, m.upper)) == m.result
    html = solution(plan(case, case["context"]))
    assert "Полученная функция чётная" not in html
    assert "разности значений" in html
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
    assert "площади под графиком" in solution(result).lower()
    assert "Контрольная работа" not in solution(result)
    context = deepcopy(original)
    context["normalized_content"]["assets"][-1]["asset_id"] = "unrelated"
    with pytest.raises(ValueError, match="unrelated"):
        plan(case, context)


def test_explicit_integral_uses_the_single_trapezoid_area_method():
    case = sample("500890")
    html = solution(plan(case, case["context"]))
    assert "Это трапеция с основаниями" in html
    assert "S_{\\mathrm{тр}}" not in html and "S_{\\mathrm{пр}}" not in html
    assert "Аналитическое решение" not in html
    assert r"S=\frac{2+4}{2}\cdot4=12" in html


def test_last_fraction_stays_separate_until_it_cancels():
    case = sample("323079")
    html = solution(plan(case, case["context"]))
    assert r"=-1017-\frac{15}{8}" in html
    assert r"=-1023-\frac{15}{8}" in html
    assert (
        r"S=F(-9)-F(-11)=\left(-1017-\frac{15}{8}\right)-\left(-1023-\frac{15}{8}\right)"
        in html
    )
    assert "=-1017+1023=6" in html
    assert r"\frac{8151}{8}" not in html
    assert r"\frac{8199}{8}" not in html


@pytest.mark.parametrize(
    "constant", [sp.Rational(15, 8), -sp.Rational(15, 8), sp.Integer(0), sp.Integer(-8)]
)
def test_one_endpoint_method_for_both_groups_with_any_constant_sign(constant):
    from solution_runner.pipelines.calculus import parabola_proof

    for task in ["323079", "323080"]:
        _, _, model = graph.calculate(sample(task)["context"])
        primitive = model.primitive - model.primitive.subs(X, 0) + constant
        changed = replace(model, primitive=primitive)
        html = parabola_proof.endpoint_values(changed)
        assert html.count("<p>Площадь выделенной фигуры") == 1
        assert "Перенесём" not in html and "Приведём" not in html
        assert (
            primitive.subs(X, model.upper) - primitive.subs(X, model.lower)
            == model.result
        )
        final = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")[-1][
            "data-inline-latex"
        ]
        assert final.endswith("=" + sp.latex(model.result))
        if constant.q > 1:
            assert r"\frac{15}{8}" not in final.split("=")[-2]


@pytest.mark.parametrize("task", ["323079", "323080"])
def test_each_endpoint_and_area_use_a_single_continuous_equality_chain(task):
    html = solution(plan(sample(task), sample(task)["context"]))
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert len(formulas) == 3
    assert formulas[0].startswith("F(") and formulas[1].startswith("F(")
    assert formulas[2].startswith("S=F(")
    assert all(not formula.startswith("=") for formula in formulas)
    assert all(formula.count("=") >= 3 for formula in formulas)


def test_fractional_negative_coefficients_have_explicit_signs_in_substitution():
    from solution_runner.pipelines.calculus import parabola_proof

    primitive = -(X**3) / 4 - 21 * X**2 / 4 - 135 * X / 4 - sp.Rational(13, 2)
    assert parabola_proof._substitution(primitive, sp.Integer(-5)) == (
        r"-\frac{1}{4}\cdot(-5)^{3}-\frac{21}{4}\cdot(-5)^{2}-\frac{135}{4}\cdot(-5)-\frac{13}{2}"
    )
    assert parabola_proof._substitution(primitive, sp.Integer(-5), powers=False) == (
        r"\frac{125}{4}-\frac{525}{4}+\frac{675}{4}-\frac{13}{2}"
    )
    assert parabola_proof._substitution(primitive, sp.Integer(-9), powers=False) == (
        r"\frac{729}{4}-\frac{1701}{4}+\frac{1215}{4}-\frac{13}{2}"
    )


@pytest.mark.parametrize(
    "value", [sp.Integer(-5), sp.Integer(0), sp.Integer(5), sp.Rational(-1, 2)]
)
def test_substitution_has_no_adjacent_signs_for_either_coefficient_sign(value):
    from solution_runner.pipelines.calculus import parabola_proof

    for primitive in [
        X**3 + 3 * X**2 + 2 * X + sp.Rational(1, 4),
        -(X**3) / 4 - 21 * X**2 / 4 - 135 * X / 4 - sp.Rational(13, 2),
    ]:
        for powers in [True, False]:
            formula = parabola_proof._substitution(primitive, value, powers=powers)
            assert "--" not in formula and "+-" not in formula and "- -" not in formula


@pytest.mark.parametrize("task", ["323078", "323183", "323185", "323275", "500890"])
def test_trapezoid_solution_has_only_bases_height_and_one_area_calculation(task):
    html = solution(plan(sample(task), sample(task)["context"]))
    soup = BeautifulSoup(html, "html.parser")
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert sum(f.startswith("S=") for f in formulas) == 1
    assert sum(f.startswith("a=") for f in formulas) == 1
    assert sum(f.startswith("b=") for f in formulas) == 1
    assert sum(f.startswith("h=") for f in formulas) == 1
    assert all(r"\int" not in f and "B_1" not in f and "B_2" not in f for f in formulas)
    assert "Аналитическое" not in html and "Приведём" not in html
    assert len(soup.find_all("img")) == 1
