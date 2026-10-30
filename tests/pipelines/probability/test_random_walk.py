"""Finite-boundary equations and explicit paths validate infinite absorption."""

from fractions import Fraction as F
from itertools import product

import pytest
from bs4 import BeautifulSoup
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.random_walk import (
    absorption_probability,
    finite_absorption,
    first_hit_mass,
)


def solve_markov_equations(p, upper):
    n = upper - 1
    matrix = [[F(i == j) for j in range(n)] + [F(0)] for i in range(n)]
    for i in range(n):
        if i:
            matrix[i][i - 1] -= 1 - p
        else:
            matrix[i][-1] = 1 - p
        if i + 1 < n:
            matrix[i][i + 1] -= p
    for col in range(n):
        pivot = matrix[col][col]
        matrix[col] = [x / pivot for x in matrix[col]]
        for i in range(n):
            if i != col:
                factor = matrix[i][col]
                matrix[i] = [
                    x - factor * y for x, y in zip(matrix[i], matrix[col], strict=True)
                ]
    return tuple(row[-1] for row in matrix)


@pytest.mark.parametrize("p", [F(0), F(1, 4), F(1, 2), F(2, 3), F(1)])
@pytest.mark.parametrize("upper", range(2, 9))
def test_finite_ruin_matches_a_separate_linear_system(p, upper):
    solved = solve_markov_equations(p, upper)
    assert finite_absorption(p, 0, upper) == 1
    assert finite_absorption(p, upper, upper) == 0
    for start, value in enumerate(solved, 1):
        assert finite_absorption(p, start, upper) == value


@pytest.mark.parametrize("p", [F(0), F(1, 4), F(1, 2), F(3, 5), F(4, 5), F(1)])
def test_absorption_is_the_correct_root_and_finite_barrier_limit(p):
    value = absorption_probability(p)
    assert value == 1 - p + p * value**2
    assert 0 <= value <= 1
    if p:
        assert value == min(F(1), (1 - p) / p)
    assert absorption_probability(p, 0) == 1
    for distance in range(1, 5):
        lower = [finite_absorption(p, distance, L) for L in (10, 20, 100)]
        assert lower == sorted(lower)
        assert lower[-1] <= absorption_probability(p, distance)
        assert absorption_probability(p, distance) - lower[-1] <= F(distance, 100)


@pytest.mark.parametrize("p", [F(1, 3), F(1, 2), F(2, 3)])
def test_catalan_first_passage_probabilities_match_all_paths(p):
    for j in range(5):
        expected = F(0)
        for steps in product((-1, 1), repeat=2 * j + 1):
            position = 1
            for index, step in enumerate(steps, 1):
                position += step
                if position == 0:
                    if index == len(steps):
                        expected += p ** steps.count(1) * (1 - p) ** steps.count(-1)
                    break
        assert first_hit_mass(p, j) == expected


@pytest.mark.parametrize("task", ["508876", "508877", "508878", "508879"])
def test_all_universal_figures_and_parent_generalizations_are_retained(task):
    case = next(c for c in CASES if c["task"] == task)
    plan = _plan(case, case["context"])
    soup = BeautifulSoup(plan.solution_html, "html.parser")
    assert len(soup.find_all("img")) == 4
    assert all(
        token in soup.get_text()
        for token in [
            "конечный барьер",
            "разорении игрока",
            "краю утёса",
            "числам Каталана",
            "отдельный иллюстративный пример",
        ]
    )
    assert len({img["data-asset-id"] for img in soup.find_all("img")}) == 4
    assert not any(
        t["transformation_target_id"].startswith("asset:") for t in plan.transformations
    )


@pytest.mark.parametrize(
    "p,distance", [(F(-1), 1), (F(2), 1), (F(1, 2), -1), (F(1, 2), 101)]
)
def test_invalid_walk_parameters_fail_closed(p, distance):
    with pytest.raises(ValueError):
        absorption_probability(p, distance)
