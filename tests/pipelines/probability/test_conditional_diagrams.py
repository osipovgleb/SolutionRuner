"""Audited diagram geometry, exact edge products and conditional-event guards."""

from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from test_complex_source_samples import CASES

from solution_runner.pipelines.probability.conditional_diagrams import (
    build_context_repair_plan,
    conditional_probability,
    tree_weights,
    uniform_points,
)

ASSETS = Path(__file__).parents[3] / "src/solution_runner/pipelines/probability/assets"


def source(task):
    case = next(
        c for c in CASES if c["group"] in ("509332", "509342") and c["task"] == task
    )
    context = deepcopy(case["context"])
    asset = context["normalized_content"]["assets"][0]
    return context, (ASSETS / (asset["asset_id"] + ".svg")).read_bytes()


@pytest.mark.parametrize(
    "task,na,nb,nab",
    [
        ("509332", 5, 4, 2),
        ("509333", 4, 2, 1),
        ("509334", 2, 4, 1),
        ("509335", 4, 5, 3),
    ],
)
def test_svg_point_membership_matches_visually_audited_regions(task, na, nb, nab):
    _, svg = source(task)
    weights, events = uniform_points(svg)
    assert len(weights) == 10 and sum(weights) == 1
    assert (len(events["A"]), len(events["B"]), len(events["A"] & events["B"])) == (
        na,
        nb,
        nab,
    )
    p, _, _ = conditional_probability(weights, events["B"], events["A"])
    assert p == F(nab, na)


@pytest.mark.parametrize("p,l,r", tuple(product((F(0), F(1, 3), F(1)), repeat=3)))
def test_binary_tree_products_preserve_mass_and_all_conditioning_events(p, l, r):
    weights = tree_weights([[p, 1 - p], [l, 1 - l], [r, 1 - r]])
    assert weights == (p * l, p * (1 - l), (1 - p) * r, (1 - p) * (1 - r))
    assert sum(weights) == 1
    for mask in range(1, 16):
        given = {i for i in range(4) if mask & (1 << i)}
        denominator = sum(weights[i] for i in given)
        if not denominator:
            with pytest.raises(ValueError):
                conditional_probability(weights, {1, 2}, given)
        else:
            actual, n, d = conditional_probability(weights, {1, 2}, given)
            assert d == denominator and n == sum(weights[i] for i in given & {1, 2})
            assert actual == n / d


@pytest.mark.parametrize(
    "kind",
    ["changed_bytes", "missing_bytes", "unknown_asset", "wrong_image", "wrong_count"],
)
def test_unverified_or_inconsistent_input_never_produces_a_plan(kind):
    context, svg = source("509332")
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if kind == "changed_bytes":
        svg += b"\n"
    if kind == "missing_bytes":
        svg = None
    if kind == "unknown_asset":
        context["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    if kind == "wrong_image":
        condition["html"] = condition["html"].replace(
            'data-asset-key="image_1"', 'data-asset-key="image_2"'
        )
    if kind == "wrong_count":
        condition["html"] = condition["html"].replace("10", "11")
    with pytest.raises(ValueError):
        build_context_repair_plan(context, condition_asset_bytes=svg)


def test_reversing_the_condition_uses_event_sets_from_the_text():
    context, svg = source("509342")
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.select_one("span[data-inline-latex]")["data-inline-latex"] = r"P(B\mid A)"
    for node, label in zip(soup.find_all("var")[-2:], ("B", "A"), strict=True):
        node["data-math-identifier"] = label
        node.string = label
    condition["html"] = str(soup)
    assert (
        build_context_repair_plan(context, condition_asset_bytes=svg).answer == "0,6875"
    )


@pytest.mark.parametrize(
    "weights,want,given",
    [
        ((F(1), F(0)), {0}, {1}),
        ((F(1, 2), F(1, 2)), {2}, {0}),
        ((F(1), F(1)), {0}, {1}),
    ],
)
def test_invalid_conditional_distributions_fail_closed(weights, want, given):
    with pytest.raises(ValueError):
        conditional_probability(weights, want, given)
