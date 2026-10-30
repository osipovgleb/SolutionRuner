"""Independent moments, collection recurrences and invalid distributions."""

from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest
from test_statistics_source_samples import CASES, _plan

from solution_runner.pipelines.statistics.common import read
from solution_runner.pipelines.statistics.estimates import chebyshev, sample_variance
from solution_runner.pipelines.statistics.moments import binomial
from solution_runner.pipelines.statistics.tables import expectation
from solution_runner.pipelines.statistics.waiting import collector, successes


@pytest.mark.parametrize("n", range(1, 7))
@pytest.mark.parametrize(
    "p", [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(1)]
)
def test_binomial_moments_agree_with_weighted_independent_trials(n, p):
    mean = second = Fraction(0)
    for row in product((0, 1), repeat=n):
        k = sum(row)
        weight = p**k * (1 - p) ** (n - k)
        mean += k * weight
        second += k * k * weight
    assert Fraction(binomial(n, p)[0].replace(",", ".")) == mean
    assert (
        Fraction(binomial(n, p, variance=True)[0].replace(",", "."))
        == second - mean * mean
    )


@pytest.mark.parametrize("n", [2, 3, 6])
def test_coupon_collection_agrees_with_first_step_recurrence(n):
    expected = Fraction(0)
    for remaining in range(1, n + 1):
        previous = expected
        expected = (1 + Fraction(remaining, n) * previous) / Fraction(remaining, n)
    assert Fraction(collector(n, n)[0].replace(",", ".")) == expected


def test_unbiased_variance_is_invariant_under_translation_and_uses_n_minus_one():
    observations = list(map(Fraction, [1, 2, 3, 4]))
    with pytest.raises(ValueError):
        sample_variance(
            observations
        )  # An exact nonterminating decimal is not silently rounded.
    observations = list(map(Fraction, [1, 2, 3]))
    assert sample_variance(observations)[0] == "1"
    assert sample_variance([x + 1000000 for x in observations])[0] == "1"
    assert sample_variance([2 * x for x in observations])[0] == "4"


@pytest.mark.parametrize(
    "weights", [[Fraction(-1), Fraction(2)], [Fraction(1, 2), Fraction(1, 4)]]
)
def test_distribution_rejects_negative_or_unnormalized_weights(weights):
    with pytest.raises(ValueError):
        expectation([Fraction(1), Fraction(2)], weights)


@pytest.mark.parametrize("p", [Fraction(-1, 10), Fraction(0), Fraction(11, 10)])
def test_waiting_times_reject_impossible_or_zero_success_probability(p):
    with pytest.raises(ValueError):
        successes(2, p)


def test_chebyshev_bounds_are_clipped_and_invalid_distances_rejected():
    assert chebyshev(Fraction(10), Fraction(1))[0] == "1"
    assert chebyshev(Fraction(10), Fraction(1), lower=True)[0] == "0"
    with pytest.raises(ValueError):
        chebyshev(Fraction(1), Fraction(0))
    with pytest.raises(ValueError):
        chebyshev(Fraction(-1), Fraction(2))


@pytest.mark.parametrize(
    ("task", "old", "new"),
    [
        ("509452", "-1", "-2"),
        ("509399", "6", "0"),
        ("509479", "пять", "шесть"),
        ("704655", "1,2", "3,2"),
        ("704659", "0,75", "1,75"),
    ],
)
def test_inconsistent_input_fails_without_changes(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    # Strip discretionary hyphens only to make the deliberate mutation readable.
    condition["html"] = condition["html"].replace("\xad", "")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    original = deepcopy(context)
    with pytest.raises(ValueError):
        _plan(case, context)
    assert context == original


def test_table_markup_does_not_hide_an_unrecognized_instruction():
    case = next(c for c in CASES if c["task"] == "509373")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        "<table", '<table style="display:none"'
    )
    with pytest.raises(ValueError):
        read(context)


@pytest.mark.parametrize("n", [4, 5])
def test_repeating_collection_expectation_is_not_silently_rounded(n):
    with pytest.raises(ValueError):
        collector(n, n)


def test_measurement_units_must_belong_to_the_measured_quantity():
    from solution_runner.pipelines.statistics.estimates import solve

    text = "Средняя длина нити в мотке пряжи равна 600 м, а стандартное отклонение равно 30 г. При помощи неравенства Чебышева найдите верхнюю оценку вероятности события «длина нити в случайно выбранном мотке отличается от средней более чем на 50 г»."
    with pytest.raises(ValueError):
        solve(text, [])
