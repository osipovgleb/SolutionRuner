"""Independent enumeration, exact threshold boundaries and complete-condition guards."""

from copy import deepcopy
from fractions import Fraction
from itertools import product
from math import comb

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.bernoulli import Trial, binomial, render
from solution_runner.pipelines.probability.event_sets import solve as solve_sets
from solution_runner.pipelines.probability.retry_threshold import minimum_attempts


@pytest.mark.parametrize("n", range(1, 6))
@pytest.mark.parametrize(
    "p", [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(1)]
)
def test_weighted_independent_events_agree_with_all_sequences(n, p):
    exact = [Fraction(0) for _ in range(n + 1)]
    any_success = Fraction(0)
    for row in product((0, 1), repeat=n):
        weight = p ** sum(row) * (1 - p) ** (n - sum(row))
        exact[sum(row)] += weight
        if any(row):
            any_success += weight
    for k in range(n + 1):
        assert binomial(n, k, p) == exact[k]
        expected = p**k * (1 - p) ** (n - k)
        answer, _ = render(Trial(n, p, "sequence", k))
        assert Fraction(answer.replace(",", ".")) == expected
    answer, _ = render(Trial(n, p, "any"))
    assert Fraction(answer.replace(",", ".")) == any_success


def test_binomial_ratio_and_fixed_order_use_different_counts():
    p = Fraction(9, 10)
    fixed, _ = render(Trial(4, p, "sequence", 2))
    assert Fraction(fixed.replace(",", ".")) == Fraction(81, 10000)
    assert binomial(4, 2, p) == comb(4, 2) * Fraction(81, 10000)
    ratio, _ = render(Trial(5, Fraction(4, 5), "ratio", 4, 3))
    assert ratio == "2"


@pytest.mark.parametrize(
    "first,p,goal",
    [
        (Fraction(1, 2), Fraction(1, 2), Fraction(3, 4)),
        (Fraction(0), Fraction(1), Fraction(1)),
        (Fraction(1), Fraction(0), Fraction(1)),
        (Fraction(2, 5), Fraction(3, 5), Fraction(49, 50)),
    ],
)
def test_minimum_attempts_includes_exact_threshold_equality(first, p, goal):
    n, previous, fail = minimum_attempts(first, p, goal)
    assert 1 - fail >= goal
    assert 1 - previous < goal
    for k in range(1, n):
        assert 1 - (1 - first) * (1 - p) ** (k - 1) < goal
    if first == p == Fraction(1, 2):
        assert n == 2


@pytest.mark.parametrize(
    "first,p,goal",
    [
        (Fraction(0), Fraction(0), Fraction(1, 2)),
        (Fraction(1, 2), Fraction(1, 2), Fraction(1)),
        (Fraction(-1), Fraction(1, 2), Fraction(1, 2)),
    ],
)
def test_unreachable_or_invalid_retry_models_fail_closed(first, p, goal):
    with pytest.raises(ValueError):
        minimum_attempts(first, p, goal)


@pytest.mark.parametrize(
    "key", ["320174", "501061", "508808", "320187", "319355", "508780"]
)
def test_all_parent_methods_remain_in_the_prepared_solution(key):
    case = next(c for c in CASES if c["task"] == key)
    html = _plan(case, case["context"]).solution_html
    markers = {
        "320174": ["Способ 2", "Способ 3"],
        "501061": ["Первый успех", "Другой способ", "противоположно"],
        "508808": ["Первый успех", "противоположно"],
        "320187": ["Решение по действиям", "сложить вероятности первого успеха"],
        "319355": ["Другой способ", "полной вероятности"],
        "508780": ["формулу Бернулли", "Другой способ"],
    }
    assert all(marker in html for marker in markers[key])


@pytest.mark.parametrize(
    "plain", ["В ответе удвойте вероятность.", "<i>В ответе удвойте вероятность.</i>"]
)
@pytest.mark.parametrize("leading", [True, False])
def test_instruction_outside_paragraphs_is_never_discarded(plain, leading):
    case = next(c for c in CASES if c["task"] == "320187")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        plain + condition["html"] if leading else condition["html"] + plain
    )
    original = deepcopy(context)
    with pytest.raises(ValueError):
        _plan(case, context)
    assert context == original


@pytest.mark.parametrize(
    "key,old,new",
    [
        ("320196", "67,01", "67,02"),
        ("320203", "до 19", "до 20"),
        ("320173", "первые три", "первые два"),
        ("320198", "больше 10", "больше 9"),
        ("508850", "0,6", "1,6"),
    ],
)
def test_inconsistent_event_boundaries_or_counts_are_rejected(key, old, new):
    case = next(c for c in CASES if c["task"] == key)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("\xad", "").replace("\u202f", " ")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    with pytest.raises(ValueError):
        _plan(case, context)


def test_disjoint_probabilities_must_not_sum_above_one():
    case = next(c for c in CASES if c["task"] == "320171")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("0,2", "0,9").replace("0,15", "0,9")
    with pytest.raises(ValueError):
        _plan(case, context)


def test_service_life_events_respect_nested_probabilities():
    text = "Вероятность того, что новый тостер прослужит больше года, равна 0,6. Вероятность того, что он прослужит больше двух лет, равна 0,8. Найдите вероятность того, что он прослужит меньше двух лет, но больше года."
    with pytest.raises(ValueError):
        solve_sets(text)
