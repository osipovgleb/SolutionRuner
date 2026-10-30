"""Full scalar-formula sources and independent domain and denominator checks."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_physical_polynomials import plan, solution

from solution_runner.pipelines.applied import algebraic_formulas as model
from solution_runner.pipelines.applied import common, formula_questions
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_formulas.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_shared_scalar_rule_registration(group):
    p = get_group_profile(group["key"])
    assert p.source_group_id == group["uuid"]
    assert p.snapshot_theme_id == group["theme_uuid"]
    assert p.theme_order_index == group["theme_order"]
    assert p.content_rule_key == group["rule"]
    assert p.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_are_computed_without_mutation_and_idempotently(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    first = plan(case, context)
    assert parse_rational(first.answer) == parse_rational(
        case.get("expected_answer", BeautifulSoup(expected, "html.parser").get_text())
    )
    assert context == original
    targets = ("section:answer", "section:solution") + (
        ("section:condition",) if case.get("expected_condition_edit") else ()
    )
    assert all(
        t["transformation_target_id"].startswith(targets) for t in first.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert plan(case, context).answer == first.answer
    context = deepcopy(original)
    for t in first.transformations:
        sections = context["normalized_content"]["sections"]
        section = next(
            (
                s
                for s in sections
                if s["transformation_target_id"] == t["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            key = t["transformation_target_id"].split(":")[1]
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(section)
        section.update(t["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unread_instructions_and_foreign_assets_cannot_be_ignored(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Отрицательные значения считайте допустимыми.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    context = deepcopy(case["context"])
    context["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(ValueError):
        plan(case, context)


def test_thermal_expansion_uses_millimetres_of_increase_not_total_length():
    _, a = model.calculate(sample("27953")["context"])
    assert a.question.target == sp.Rational(3, 1000) and a.result == 25
    assert a.expression.subs(a.question.variable, 25) == sp.Rational(3, 1000)
    html = solution(plan(sample("28017"), sample("28017")["context"]))
    assert "37{,}5" in html and r"\text{{}^{\circ}" not in html


def test_profit_is_a_count_and_can_be_negative_without_allowing_negative_production():
    _, a = model.calculate(sample("27954")["context"])
    q = a.question
    loss = model.analyze(replace(q, target=sp.Integer(-699400)))
    assert loss.result == 3
    with pytest.raises(ValueError, match="nonnegative"):
        model.analyze(replace(q, target=sp.Integer(-700200)))
    with pytest.raises(ValueError, match="whole"):
        model.analyze(replace(q, target=sp.Integer(1)))
    v = {
        **q.values,
        "price": sp.Integer(10),
        "cost": sp.Integer(20),
        "overhead": sp.Integer(100),
    }
    loss = model.analyze(
        replace(q, values=v, target=sp.Integer(-130), expression=-10 * q.variable - 100)
    )
    assert loss.result == 3
    with pytest.raises(ValueError, match="unique affine"):
        model.analyze(
            replace(
                q,
                values={**q.values, "price": q.values["cost"]},
                expression=-q.values["overhead"],
                target=-q.values["overhead"],
            )
        )


def test_market_equation_and_revenue_threshold_remain_different_requests():
    _, at_least = model.calculate(sample("27956")["context"])
    _, equal = model.calculate(sample("500168")["context"])
    assert at_least.question.relation == "ge" and at_least.roots == (4, 6)
    assert equal.question.relation == "eq" and equal.roots == (6, 10)
    assert at_least.result == 6 and equal.result == 10
    zero = model.analyze(replace(at_least.question, target=sp.Integer(0)))
    assert zero.result == zero.domain_end == 10
    tangent = model.analyze(replace(at_least.question, target=sp.Integer(250)))
    assert tangent.result == 5
    with pytest.raises(ValueError, match="no price"):
        model.analyze(replace(at_least.question, target=sp.Integer(251)))


def test_pressure_cancels_positive_mass_and_converts_centimetres():
    _, a = model.calculate(sample("27958")["context"])
    assert a.ratio == 4 and a.result == 2
    assert a.expression == sp.Rational(5, 2) * a.question.variable**2 - 10
    html = solution(plan(sample("27958"), sample("27958")["context"]))
    assert "Масса воды положительна" in html and "10^{-2}" in html


def test_original_zero_denominators_are_refused_even_when_they_would_cancel():
    x = sp.Symbol("x", real=True)
    with pytest.raises(ValueError, match="denominator"):
        formula_questions.bind(r"\frac{lx}{l}", x, {"l": sp.Integer(0)})
    with pytest.raises(ValueError, match="denominator"):
        formula_questions.bind(r"\frac{x}{l}", x, {"l": x + 1})
    assert formula_questions.bind(r"\frac{lx}{l}", x, {"l": sp.Integer(2)}) == x


def test_inertia_uses_only_nonnegative_radial_addition():
    _, a = model.calculate(sample("27966")["context"])
    assert a.roots == (-25, 5) and a.result == 5
    at_zero = model.analyze(replace(a.question, target=sp.Integer(500)))
    assert at_zero.result == 0
    with pytest.raises(ValueError, match="nonnegative"):
        model.analyze(replace(a.question, target=sp.Integer(499)))


@pytest.mark.parametrize(
    "task,expected",
    [
        ("41741", sp.Rational(16, 5)),
        ("704222", sp.Integer(3)),
        ("500914", sp.Integer(6000)),
    ],
)
def test_large_exact_powers_and_fractional_roots_are_not_float_approximations(
    task, expected
):
    _, a = model.calculate(sample(task)["context"])
    assert a.result == expected and a.result**a.power == a.ratio
    assert a.result.is_Rational


def test_nonrational_positive_root_is_not_silently_rounded():
    _, a = model.calculate(sample("27967")["context"])
    with pytest.raises(ValueError, match="without rounding"):
        model.analyze(replace(a.question, target=sp.Integer(19600)))


def test_force_subscript_is_only_allowed_on_the_force_identifier():
    assert "F_A=" in common.read(sample("27968")["context"])[3]
    context = deepcopy(sample("27968")["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        'data-math-identifier="F">F', 'data-math-identifier="G">G'
    )
    with pytest.raises(ValueError, match="subscripts"):
        common.read(context)


def test_parameter_or_unit_changes_do_not_reuse_the_old_computation():
    case = sample("27958")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("\u00ad", "").replace("см?", "м?")
    with pytest.raises(ValueError):
        plan(case, context)
    _, a = model.calculate(sample("27967")["context"])
    with pytest.raises(ValueError, match="contradicts"):
        model.analyze(replace(a.question, expression=a.expression / 2))


@pytest.mark.parametrize("task", ["27973", "27978", "27988", "27989"])
def test_inverse_powers_use_the_strict_positive_domain_and_exact_boundary(task):
    _, a = model.calculate(sample(task)["context"])
    q = a.question
    assert a.result > 0 and a.result**a.power == a.ratio
    assert a.expression.subs(q.variable, a.result) == q.target
    assert a.expression.subs(q.variable, a.result / 2) > q.target
    assert a.expression.subs(q.variable, 2 * a.result) < q.target
    html = solution(plan(sample(task), sample(task)["context"]))
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert q.label + ">0" in formulas
    for target in [sp.Integer(0), sp.Integer(-1)]:
        with pytest.raises(ValueError):
            model.analyze(replace(q, target=target))
    for key in q.values.keys() - {"target"}:
        with pytest.raises(ValueError):
            model.analyze(replace(q, values={**q.values, key: sp.Integer(0)}))
    with pytest.raises(ValueError, match="contradicts"):
        model.analyze(replace(q, expression=q.expression * q.variable))


def test_traction_equality_has_no_maximum_or_inequality():
    _, bound = model.calculate(sample("27989")["context"])
    _, equal = model.calculate(sample("517196")["context"])
    assert bound.question.relation == "ge" and equal.question.relation == "eq"
    html = solution(plan(sample("517196"), sample("517196")["context"]))
    assert r"\leq" not in html and r"\max" not in html
    text = common.read(sample("517196")["context"])[3].replace(
        "Определите время", "Определите наибольшее время"
    )
    with pytest.raises(ValueError, match="request"):
        formula_questions.parse(text)


def test_bad_saved_fuse_answer_is_recomputed_from_voltage_and_current():
    case = sample("28237")
    saved = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(saved, "html.parser").get_text() == "000"
    assert parse_rational(plan(case, case["context"]).answer) == sp.Rational(44, 5)


def test_variable_denominators_need_an_explicit_positive_domain():
    x = sp.Symbol("x", real=True)
    with pytest.raises(ValueError, match="denominator"):
        formula_questions.bind(r"\frac{1}{x}", x, {})
    assert (
        formula_questions.bind(r"\frac{1}{x^2}", x, {}, positive_variable=True) == x**-2
    )
    with pytest.raises(ValueError, match="denominator"):
        formula_questions.bind(
            r"\frac{1}{lx}", x, {"l": sp.Integer(0)}, positive_variable=True
        )
    _, a = model.calculate(sample("27988")["context"])
    with pytest.raises(ValueError, match="without rounding"):
        model.analyze(replace(a.question, target=sp.Integer(3)))


def test_boiler_uses_temperature_increase_and_positive_wood_mass():
    case = sample("27977")
    _, a = model.calculate(case["context"])
    assert a.expression == 378 / a.question.variable and a.result == 18
    html = solution(plan(case, case["context"]))
    assert r"\Delta t=100-10=90" in html
    assert r"{m_{\mathrm{др}}}_{\min}" in html
    for target in [sp.Integer(0), sp.Integer(-1), sp.Integer(101)]:
        with pytest.raises(ValueError):
            model.analyze(replace(a.question, target=target))
    at_100 = model.analyze(replace(a.question, target=sp.Integer(100)))
    assert at_100.result == sp.Rational(189, 50)
    for key in ["heat", "fuel", "water"]:
        with pytest.raises(ValueError):
            model.analyze(
                replace(a.question, values={**a.question.values, key: sp.Integer(0)})
            )


def test_boiler_rejects_cooling_and_changes_to_the_water_or_wood_subscript():
    text = common.read(sample("27977")["context"])[3]
    with pytest.raises(ValueError, match="heating"):
        model.analyze(
            formula_questions.parse(
                text.replace("от 10 °C до 100 °C", "от 100 °C до 10 °C")
            )
        )
    context = deepcopy(sample("27977")["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("<sub>др</sub>", "<sub>д</sub>")
    with pytest.raises(ValueError, match="subscripts"):
        model.calculate(context)
    condition["html"] = condition["html"].replace("<sub>д</sub>", "<sub>в</sub>")
    with pytest.raises(ValueError, match="recognized"):
        model.calculate(context)
