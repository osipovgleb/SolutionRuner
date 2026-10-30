"""Independent exhaustive tournament trees, including random byes."""

from copy import deepcopy
from fractions import Fraction
from functools import cache
from itertools import product

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.knockout import meeting_rounds


def pairings(players):
    if not players:
        yield ()
        return
    first, *remaining = players
    for opponent in remaining:
        others = tuple(p for p in remaining if p != opponent)
        for rest in pairings(others):
            yield ((first, opponent),) + rest


@cache
def enumerate_meeting(players):
    if 0 not in players or 1 not in players or len(players) < 2:
        return Fraction(0)
    arrangements = []
    for bye in players if len(players) % 2 else (None,):
        for pairs in pairings(tuple(p for p in players if p != bye)):
            arrangements.append((bye, pairs))
    total = Fraction(0)
    for bye, pairs in arrangements:
        if (0, 1) in pairs:
            total += 1
            continue
        for winners in product(*pairs):
            next_round = tuple(sorted(winners + ((bye,) if bye is not None else ())))
            total += enumerate_meeting(next_round) / 2 ** len(pairs)
    return total / len(arrangements)


@pytest.mark.parametrize("n", range(2, 8))
def test_all_matching_and_winner_outcomes_agree_with_round_recurrence(n):
    probabilities = [p for _, p in meeting_rounds(n)]
    assert sum(probabilities) == enumerate_meeting(tuple(range(n))) == Fraction(2, n)


@pytest.mark.parametrize("n", [0, 1, 4097])
def test_unsupported_tournament_sizes_fail_closed(n):
    with pytest.raises(ValueError):
        meeting_rounds(n)


def test_odd_round_requires_explicit_bye_rule():
    case = next(c for c in CASES if c["task"] == "508870")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("16", "10")
    with pytest.raises(ValueError):
        _plan(case, context)


def test_all_three_methods_are_retained_for_random_byes():
    case = next(c for c in CASES if c["task"] == "508873")
    plan = _plan(case, case["context"])
    assert plan.answer == "0,2"
    for method in ["Способ 1", "Способ 2", "Способ 3", "При нечётном"]:
        assert method in plan.solution_html
