"""Conditional rank weights checked against all random tournament orders."""

from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import permutations

import pytest
from bs4 import BeautifulSoup
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.record_tournaments import record_ranks


@pytest.mark.parametrize("n", range(3, 9))
def test_rank_distribution_and_next_win_match_all_orders(n):
    orders = list(permutations(range(1, n + 1)))
    for k in range(1, n - 1):
        ranks = Counter()
        won = 0
        for row in orders:
            if row[0] > max(row[1 : k + 1]):
                ranks[row[0]] += 1
                won += row[0] > row[k + 1]
        rows, total = record_ranks(n, k)
        seen = sum(ranks.values())
        assert sum(ways for _, ways, _ in rows) == total
        for r, ways, _ in rows:
            assert F(ranks[r], seen) == F(ways, total)
        p = sum(F(ways, total) * prob for _, ways, prob in rows)
        assert p == F(won, seen) == F(k + 1, k + 2)


@pytest.mark.parametrize("n,k", [(2, 1), (31, 1), (6, 0), (6, 5), (6, 6)])
def test_a_next_opponent_must_still_exist(n, k):
    with pytest.raises(ValueError):
        record_ranks(n, k)


@pytest.mark.parametrize("task", ["508866", "508867", "508868", "508869"])
def test_all_six_methods_and_the_proof_reference_survive(task):
    case = next(c for c in CASES if c["task"] == task)
    plan = _plan(case, case["context"])
    soup = BeautifulSoup(plan.solution_html, "html.parser")
    for k in range(1, 7):
        assert f"Способ {k}." in soup.get_text()
    links = soup.find_all("a")
    assert len(links) == 1
    if task == "508866":
        assert links[0]["data-asset-key"] == "attachment_1"
        assert links[0]["href"] == "/assets/42e02105-7c04-445a-866c-8159f3c00697"
        assert (
            plan.solution_html.index("Способ 1.")
            < plan.solution_html.index("<a ")
            < plan.solution_html.index("Способ 2.")
        )
    else:
        assert links[0]["href"] == "https://math-ege.sdamgia.ru/get_file?id=135669"
        assert "data-asset-key" not in links[0].attrs
    assert "Вероятность следующей победы" in soup.get_text()


def test_the_requested_round_is_checked_instead_of_inferred_from_the_answer():
    case = next(c for c in CASES if c["task"] == "508866")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    original = condition["html"].replace("\xad", "").replace("ё", "е")
    condition["html"] = original.replace("четвертый", "пятый")
    assert condition["html"] != original
    with pytest.raises(ValueError):
        _plan(case, context)
