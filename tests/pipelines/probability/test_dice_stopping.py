"""Exhaustive finite horizons distinguish weighted hitting paths from raw counts."""

from fractions import Fraction
from itertools import product

import pytest

from solution_runner.pipelines.probability.dice_stopping import (
    conditional_hitting_probability,
    hitting_counts,
)


@pytest.mark.parametrize("total", range(1, 7))
def test_first_hitting_time_matches_equal_length_full_outcomes(total):
    hits = [0] * total
    for rolls in product(range(1, 7), repeat=total):
        cumulative = 0
        for index, face in enumerate(rolls):
            cumulative += face
            if cumulative == total:
                hits[index] += 1
            if cumulative >= total:
                break
    denominator = sum(hits)
    for k, h in enumerate(hits, 1):
        probability, counts, _ = conditional_hitting_probability(total, k)
        assert probability == Fraction(h, denominator)
        assert h == counts[k - 1] * 6 ** (total - k)


def test_six_sided_bound_is_respected_for_larger_sums():
    assert hitting_counts(7)[0] == 0
    assert hitting_counts(7)[1] == 6
    probability, _, _ = conditional_hitting_probability(4, 1)
    assert probability == Fraction(216, 343)
    assert probability != Fraction(1, 8)


@pytest.mark.parametrize("total,throws", [(0, 1), (61, 1), (4, 0), (4, 5)])
def test_invalid_hitting_models_fail_closed(total, throws):
    with pytest.raises(ValueError):
        conditional_hitting_probability(total, throws)


def test_reused_and_generated_trees_mark_the_requested_hitting_time():
    from xml.etree import ElementTree as ET

    from solution_runner.pipelines.probability.dice_stopping import render_svg

    for total in range(1, 5):
        for throws in range(1, total + 1):
            root = ET.fromstring(render_svg(total, throws))
            marked = [
                n
                for n in root.iter()
                if n.tag.endswith("circle") and n.attrib.get("fill") == "#9bd3ab"
            ]
            assert len(marked) == hitting_counts(total)[throws - 1]
            assert {float(n.attrib["cy"]) for n in marked} == {50 + 90 * throws}
    with pytest.raises(ValueError):
        render_svg(5, 2)
