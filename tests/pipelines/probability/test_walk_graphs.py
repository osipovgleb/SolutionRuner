"""Forward paths are checked against a separate time-step probability process."""

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from pathlib import Path

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability.walk_graphs import (
    build_context_repair_plan,
    forward_paths,
    svg_graph,
)

ASSETS = Path(__file__).parents[3] / "src/solution_runner/pipelines/probability/assets"


def time_step_distribution(n, edges):
    adjacency = [set() for _ in range(n)]
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    active = {(None, 0): F(1)}
    terminal = defaultdict(F)
    for _ in range(n):
        next_active = defaultdict(F)
        for (parent, node), weight in active.items():
            options = adjacency[node] - {parent}
            if not options:
                terminal[node] += weight
            for nxt in options:
                next_active[node, nxt] += weight / len(options)
        active = next_active
    assert not active
    return dict(terminal)


@pytest.mark.parametrize("n", range(2, 7))
def test_all_recursive_trees_match_the_stepwise_distribution(n):
    for parents in product(*(range(k) for k in range(1, n))):
        edges = tuple((k, p) for k, p in enumerate(parents, 1))
        actual = {}
        for leaf, path, factors in forward_paths(n, edges, 0):
            probability = F(1)
            for factor in factors:
                probability *= factor
            actual[leaf] = probability
            assert len(path) == len(factors) + 1
        assert actual == time_step_distribution(n, edges)
        assert sum(actual.values()) == 1


def test_svg_graph_geometry_matches_the_audited_park():
    svg = (ASSETS / "7ba4c5dd-126e-4116-9163-9088a61f4be4.svg").read_bytes()
    _, points, edges = svg_graph(svg)
    assert len(points) == 18 and len(edges) == 17
    actual = {}
    for leaf, _, factors in forward_paths(len(points), edges, 0):
        p = F(1)
        for factor in factors:
            p *= factor
        actual[leaf] = p
    assert actual[7] == F(1, 16)  # Fountain.
    assert sum(actual[i] for i in (9, 10, 11)) == F(1, 4)  # Three pond paths.
    assert sum(actual[i] for i in (13, 14, 15)) == F(1, 4)  # Three playground paths.
    assert sum(actual.values()) == 1


@pytest.mark.parametrize(
    "n,edges,start",
    [
        (3, ((0, 1), (1, 0)), 0),
        (4, ((0, 1), (1, 2), (2, 0)), 0),
        (2, ((0, 2),), 0),
        (2, ((0, 1),), 2),
    ],
)
def test_non_tree_or_invalid_graphs_fail_closed(n, edges, start):
    with pytest.raises(ValueError):
        forward_paths(n, edges, start)


def test_changing_a_drawn_endpoint_is_not_guessed():
    svg = (ASSETS / "7ba4c5dd-126e-4116-9163-9088a61f4be4.svg").read_bytes()
    with pytest.raises(ValueError):
        svg_graph(svg.replace(b'x1="44.8384"', b'x1="0"'))


def test_missing_or_incompatible_solution_figure_cannot_be_reused():
    case = next(c for c in CASES if c["task"] == "562240")
    context = deepcopy(case["context"])
    context["normalized_content"]["assets"] = [
        a
        for a in context["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    ]
    with pytest.raises(ValueError):
        build_context_repair_plan(
            context,
            condition_asset_bytes=(
                ASSETS / "7ba4c5dd-126e-4116-9163-9088a61f4be4.svg"
            ).read_bytes(),
        )


def test_parent_figure_position_and_two_of_four_roads_are_preserved():
    case = next(c for c in CASES if c["task"] == "562239")
    html = _plan(case, case["context"]).solution_html
    assert (
        html.index("Пути к фонтану") < html.index("<img") < html.index("Пути к пруду")
    )
    assert "2 из 4" in html
