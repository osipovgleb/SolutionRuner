"""Ordered finite draws and explicit local repair of an incomplete stopping rule."""

from copy import deepcopy
from fractions import Fraction
from itertools import permutations
from xml.etree import ElementTree as ET

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.draw_tree import render_svg
from solution_runner.pipelines.probability.without_replacement import (
    ordered_draw_probability,
)


@pytest.mark.parametrize("red,blue", [(0, 2), (1, 2), (2, 1), (3, 2), (4, 2)])
def test_first_blue_matches_permutations_of_distinct_markers(red, blue):
    orders = list(permutations(range(red + blue)))
    for position in range(1, red + 2):
        favorable = sum(
            next(i for i, x in enumerate(order, 1) if x >= red) == position
            for order in orders
        )
        value, _ = ordered_draw_probability((0,) * (position - 1) + (1,), blue, red)
        assert value == Fraction(favorable, len(orders))


def test_new_draw_tree_shows_all_remaining_populations_without_clipping():
    for red, blue, position in [(5, 3, 3), (25, 5, 5), (0, 2, 1)]:
        root = ET.fromstring(render_svg(red, blue, position))
        circles = [n for n in root.iter() if n.tag.endswith("circle")]
        assert len(circles) == sum(red + blue - k + 2 for k in range(position))
        width = float(root.attrib["width"])
        height = float(root.attrib["height"])
        for n in circles:
            x = float(n.attrib["cx"])
            y = float(n.attrib["cy"])
            r = float(n.attrib["r"])
            assert r <= x <= width - r and r <= y <= height - r


@pytest.mark.parametrize("task", ["674923", "674962"])
def test_incomplete_condition_is_explicitly_repaired_before_answer(task):
    case = next(c for c in CASES if c["task"] == task)
    original = deepcopy(case["context"])
    plan = _plan(case, original)
    change = next(
        t
        for t in plan.transformations
        if t["transformation_target_id"].startswith("section:condition")
    )
    assert change["operation"] == "rewrite"
    assert "до первого момента" in change["value"]["html"]
    assert (
        "Известно, что в этот момент сумма оказалась равна 3" in change["value"]["html"]
    )
    assert plan.answer == ("0,73" if task == "674923" else "0,24")
    assert original == case["context"]


def test_unknown_stopping_instruction_is_not_reinterpreted_as_the_audited_repair():
    case = next(c for c in CASES if c["task"] == "674962")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] += "<p>Число бросков выбирается равновероятно из 1 и 2.</p>"
    with pytest.raises(ValueError):
        _plan(case, context)
