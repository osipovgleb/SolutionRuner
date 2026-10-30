"""Weighted normalization, checked prose and distinct power/product store laws."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_algebraic_formulas import (
    test_shared_scalar_rule_registration as verify_registration,
)
from test_algebraic_formulas import (
    test_source_answers_are_computed_without_mutation_and_idempotently as verify_source,
)
from test_algebraic_formulas import (
    test_unread_instructions_and_foreign_assets_cannot_be_ignored as verify_rejection,
)
from test_physical_polynomials import plan

from solution_runner.pipelines.applied import common
from solution_runner.pipelines.applied import rating_models as model
from solution_runner.pipelines.applied import rating_questions as questions
from solution_runner.pipelines.applied.rating_questions import A, B, D, E, X

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_ratings.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = questions.normalize(common.read(sample(task)["context"])[3])
    assert old in text
    return model.analyze(questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_five_groups_share_one_rating_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replays_compute_answers_independently_and_idempotently(case):
    verify_source(case)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_foreign_assets_and_unread_instructions_are_refused(case, leading):
    verify_rejection(case, leading)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"317096", "319859", "319860"}],
    ids=lambda c: c["task"],
)
def test_weighted_law_gives_the_required_rating_on_the_full_reviewed_integer_scale(
    case,
):
    _, a = model.calculate(case["context"])
    q = a.question
    actual = questions.weighted_formula(q.formula).subs(X, a.result)
    scores = (
        range(int(q.values["lower"]), int(q.values["upper"]) + 1)
        if q.kind == "identity"
        else [q.values["upper"]]
    )
    for score in scores:
        rating = actual.subs({A: score, B: score, D: score, E: score})
        assert rating == (score if q.kind == "identity" else q.values["target"])


def test_five_point_scale_can_have_negative_labels_and_maximum_two():
    _, a = model.calculate(sample("319861")["context"])
    assert a.question.values["upper"] == 2 and a.numerator == 18 and a.result == 2
    with pytest.raises(ValueError, match="scale length"):
        changed("319861", "от -2 до 2", "от -2 до 3")


def test_identity_including_zero_requires_a_nonzero_allowed_score():
    with pytest.raises(ValueError, match="uniquely"):
        changed("319860", "от -2 до 2", "от 0 до 0")
    with pytest.raises(ValueError, match="integer rating scale"):
        changed("319860", "от -2 до 2", "от 3 до 2")
    with pytest.raises(ValueError, match="zero target"):
        changed("317096", "рейтинг 30", "рейтинг 0")
    with pytest.raises(ValueError, match="positive"):
        changed("317096", "рейтинг 30", "рейтинг -30")


def test_audited_weight_repair_changes_only_the_prose_word():
    case = sample("319961")
    prepared = plan(case, case["context"])
    original = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    before, after = [
        BeautifulSoup(html, "html.parser")
        for html in [original, prepared.condition_html]
    ]
    assert [
        tag["data-inline-latex"] for tag in before.select("[data-inline-latex]")
    ] == [tag["data-inline-latex"] for tag in after.select("[data-inline-latex]")]
    assert before.get_text().replace("\u00ad", "").count("втрое") == 1
    assert "вчетверо" in after.get_text() and prepared.answer == "11"
    with pytest.raises(ValueError, match="prose weights"):
        changed("319961", "5In+Op+4Tr+Q", "5In+Op+5Tr+Q")
    with pytest.raises(ValueError, match="prose weights"):
        changed("317096", "3In+Op+2Tr", "4In+Op+2Tr")


def test_original_weighted_and_store_denominator_holes_are_not_cancelled_away():
    with pytest.raises(ValueError, match="original denominators"):
        changed("317096", r"\frac{3In+Op+2Tr}{A}", r"\frac{(3In+Op+2Tr)(A-1)}{A(A-1)}")
    with pytest.raises(ValueError, match="denominator"):
        changed("317098", "равно 20", "равно 0")
    with pytest.raises(ValueError, match="denominator"):
        changed("317097", "равна 0,86", "равна -0,1")


def test_power_and_product_are_distinct_and_rational_roots_are_exact():
    _, power = model.calculate(sample("317097")["context"])
    _, product = model.calculate(sample("317098")["context"])
    _, cube = model.calculate(sample("509575")["context"])
    assert power.exponent == sp.Rational(1, 2) and power.denominator == 5
    assert cube.exponent == sp.Rational(1, 3) and cube.denominator == 2
    assert product.denominator == sp.Rational(56, 5) and product.result == sp.Rational(
        5, 8
    )
    with pytest.raises(ValueError, match="rating law"):
        changed("317097", r"(K+1)^{m}", r"(K+1)m")
    with pytest.raises(ValueError, match="rating law"):
        changed("317098", r"0{,}02K", r"0{,}03K")
    with pytest.raises(ValueError, match="without rounding"):
        changed("317097", "равно 24", "равно 25")
    zero_count = changed("317097", "равно 24", "равно 0")
    assert zero_count.result == sp.Rational(11, 100)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("317098", "равна 0,65", "равна 1,01"),
        ("317098", "равна 0,37", "равна 0,71"),
        ("317098", "равно 20", "равно 20,5"),
        ("317097", "равно 24", "равно -1"),
    ],
)
def test_declared_domains_and_integer_customer_counts_are_checked(task, old, new):
    with pytest.raises(ValueError):
        changed(task, old, new)


@pytest.mark.parametrize("task,answer", [("317267", "0,75"), ("317269", "0,785")])
def test_incorrect_saved_store_answers_are_recomputed(task, answer):
    case = sample(task)
    saved = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(saved, "html.parser").get_text() in {"000", "150"}
    assert plan(case, case["context"]).answer == answer


def test_cyrillic_rating_subscripts_only_belong_to_the_rating_variable():
    context = deepcopy(sample("317098")["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    previous = soup.find("sub", string="пок").previous_sibling
    assert "r" in str(previous)
    previous.replace_with("s")
    condition["html"] = str(soup)
    with pytest.raises(ValueError, match="subscripts"):
        common.read(context)
