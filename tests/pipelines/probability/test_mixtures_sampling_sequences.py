"""Independent checks for mixtures, conditional samples and two-state paths."""

from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability import (
    custom_dice,
    finite_sequences,
    mixtures,
)
from solution_runner.pipelines.probability.without_replacement import (
    hypergeometric_counts,
    ordered_draw_probability,
)


def test_total_probability_and_inverse_weight_match_a_counted_population():
    # 48 of 120 belong to source 1; it contributes 12 successes, source 2 contributes 48.
    assert mixtures.total_probability(
        Fraction(2, 5), Fraction(1, 4), Fraction(2, 3)
    ) == Fraction(60, 120)
    assert mixtures.mixture_weight(
        Fraction(1, 4), Fraction(2, 3), Fraction(1, 2)
    ) == Fraction(48, 120)


@pytest.mark.parametrize(
    "a,b,total",
    [
        (Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)),
        (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)),
        (Fraction(-1), Fraction(1, 2), Fraction(0)),
    ],
)
def test_underdetermined_or_inconsistent_mixtures_fail_closed(a, b, total):
    with pytest.raises(ValueError):
        mixtures.mixture_weight(a, b, total)


def test_egg_child_keeps_all_methods_of_its_own_parent():
    child = next(c for c in CASES if c["group"] == "320177" and c["task"] == "320751")
    singleton = next(c for c in CASES if c["group"] == "320751")
    rich = _plan(child, child["context"])
    short = _plan(singleton, singleton["context"])
    assert rich.answer == short.answer == "0,6"
    assert "Ещё один способ" in rich.solution_html
    assert "отношении 3:2" in rich.solution_html
    assert "Ещё один способ" not in short.solution_html


@pytest.mark.parametrize(
    "group,markers",
    [
        ("320180", ["Другой способ", "событие A означает попадание"]),
        ("320200", ["Числовая модель", "поступают все качественные"]),
        ("508819", ["формуле Байеса", "Другой способ"]),
        ("508887", ["Способ 1", "Способ 2", "Формальная запись"]),
        ("500998", ["Способ 1", "Способ 2", "Способ 3", "Способ 4"]),
    ],
)
def test_multi_method_parents_are_preserved(group, markers):
    case = next(c for c in CASES if c["task"] == group and c["group"] == group)
    html = _plan(case, case["context"]).solution_html
    assert all(marker in html for marker in markers)


@pytest.mark.parametrize("p", [Fraction(0), Fraction(1, 4), Fraction(1, 2)])
def test_football_scoring_matches_closed_form_for_conventional_scores(p):
    outcomes = finite_sequences.football_outcomes(3, 1, p, 4)
    assert sum((weight for _, _, weight in outcomes), Fraction(0)) == p * p + 2 * p * (
        1 - 2 * p
    )
    assert (
        sum(
            (w for _, _, w in finite_sequences.football_outcomes(3, 1, p, 0)),
            Fraction(0),
        )
        == 1
    )
    assert (
        sum(
            (w for _, _, w in finite_sequences.football_outcomes(3, 1, p, 7)),
            Fraction(0),
        )
        == 0
    )


@pytest.mark.parametrize("n", range(1, 6))
@pytest.mark.parametrize(
    "p", [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(1)]
)
@pytest.mark.parametrize("end", [0, 1])
def test_weather_paths_agree_with_the_two_state_closed_form(n, p, end):
    outcomes = finite_sequences.weather_outcomes(n, p, 0, end)
    same = (1 + (2 * p - 1) ** n) / 2
    assert sum((weight for _, weight, _ in outcomes), Fraction(0)) == (
        same if end == 0 else 1 - same
    )


@pytest.mark.parametrize(
    "total,good,n", [(6, 2, 3), (9, 5, 4), (10, 7, 5), (8, 7, 5), (5, 0, 2), (5, 5, 2)]
)
def test_hypergeometric_counts_agree_with_labeled_subsets(total, good, n):
    denominator, rows = hypergeometric_counts(total, good, n, lambda k: k <= 1)
    subsets = list(combinations(range(total), n))
    favorable = sum(sum(i < good for i in subset) <= 1 for subset in subsets)
    assert denominator == len(subsets)
    assert sum(count for _, count, selected in rows if selected) == favorable
    assert sum(count for _, count, _ in rows) == denominator


def test_stopping_at_the_sixth_success_conditions_on_the_final_attempt():
    outcomes = [
        bits for bits in product((0, 1), repeat=10) if bits[-1] == 1 and sum(bits) == 6
    ]
    value = Fraction(sum(sum(bits[:4]) <= 1 for bits in outcomes), len(outcomes))
    assert value == Fraction(1, 6)
    case = next(c for c in CASES if c["task"] == "663478")
    assert _plan(case, case["context"]).answer == "0,167"


def test_two_rare_coins_split_probability_matches_all_labeled_subsets():
    cases = [c for c in CASES if c["group"] == "500998"]
    subsets = list(combinations(range(6), 3))
    split = Fraction(sum(sum(i < 2 for i in s) == 1 for s in subsets), len(subsets))
    assert split == Fraction(3, 5)
    assert _plan(cases[0], cases[0]["context"]).answer == "0,6"
    assert _plan(cases[1], cases[1]["context"]).answer == "0,4"
    assert ordered_draw_probability((1, 0, 0), 2, 4)[0] == Fraction(1, 5)


def test_custom_die_face_multiplicity_is_not_treated_as_uniform_labels():
    faces = [1, 1, 2, 2, 3, 3]
    assert len(custom_dice.outcomes(faces, (1, 1))) == 4
    assert len(custom_dice.outcomes(faces, (1, 2))) == 8
    with pytest.raises(ValueError):
        custom_dice.outcomes([1, 2], (1, 2))


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("319353", "55%", "56%"),
        ("320177", "35%", "95%"),
        ("320180", "10 револьверов", "1 револьверов"),
        ("508819", "94%", "10%"),
        ("663475", "все восемь", "все семь"),
    ],
)
def test_inconsistent_parameters_cannot_produce_a_plan(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("\xad", "").replace("\u202f", " ")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    original = deepcopy(context)
    with pytest.raises(ValueError):
        _plan(case, context)
    assert context == original
