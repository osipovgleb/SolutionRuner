"""First passage is checked by exhaustive rolls and independent SVG markers."""

from fractions import Fraction as F
from itertools import product
from xml.etree import ElementTree as ET

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.dice_stopping import first_exceed_probability
from solution_runner.pipelines.probability.exceed_figures import (
    render_table,
    render_tree,
)


@pytest.mark.parametrize("threshold", range(1, 6))
def test_crossing_time_matches_all_full_roll_sequences(threshold):
    for throws in range(1, threshold + 2):
        favorable = 0
        for rolls in product(range(1, 7), repeat=throws):
            s = 0
            first = None
            for k, face in enumerate(rolls, 1):
                s += face
                if s > threshold:
                    first = k
                    break
            favorable += first == throws
        p, n, _ = first_exceed_probability(threshold, throws)
        assert n == favorable and p == F(favorable, 6**throws)


@pytest.mark.parametrize("threshold", range(1, 16))
def test_all_possible_stopping_times_form_a_distribution(threshold):
    assert (
        sum(first_exceed_probability(threshold, k)[0] for k in range(1, threshold + 2))
        == 1
    )
    if threshold >= 6:
        assert first_exceed_probability(threshold, 1)[0] == 0


@pytest.mark.parametrize("threshold", range(1, 5))
def test_both_figures_encode_the_computed_event(threshold):
    for throws in range(1, min(3, threshold + 1) + 1):
        p, n, _ = first_exceed_probability(threshold, throws)
        tree = ET.fromstring(render_tree(threshold, throws))
        assert (
            sum(
                F(node.attrib["data-success-probability"])
                for node in tree.iter()
                if "data-success-probability" in node.attrib
            )
            == p
        )
        table = ET.fromstring(render_table(threshold, throws))
        assert sum("data-face" in node.attrib for node in table.iter()) == n


@pytest.mark.parametrize("threshold,throws", [(0, 1), (61, 1), (3, 0), (3, 5)])
def test_invalid_crossing_models_fail_closed(threshold, throws):
    with pytest.raises(ValueError):
        first_exceed_probability(threshold, throws)


@pytest.mark.parametrize("task", ["508797", "508798", "508799", "508800"])
def test_all_three_parent_methods_remain_in_each_prepared_solution(task):
    case = next(c for c in CASES if c["task"] == task)
    plan = _plan(case, case["context"])
    assert all(f"Способ {i}" in plan.solution_html for i in (1, 2, 3))
    assert plan.solution_html.count("<img") == 2
    assert (
        plan.solution_html.index("Способ 1")
        < plan.solution_html.index("Способ 2")
        < plan.solution_html.index("Способ 3")
    )
