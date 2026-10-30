"""Audited corridors, terminal dead ends and all exit probabilities are verified."""

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from test_complex_source_samples import CASES, _condition_bytes, _plan
from test_walk_graphs import time_step_distribution

from solution_runner.pipelines.probability.walk_graphs import (
    build_context_repair_plan,
    forward_paths,
)

ASSETS = Path(__file__).parents[3] / "src/solution_runner/pipelines/probability/assets"
DATA = json.loads((ASSETS / "maze_diagrams.json").read_text())


@pytest.mark.parametrize("asset,entry", DATA.items())
def test_all_terminal_probabilities_match_a_separate_stepwise_process(asset, entry):
    source = (ASSETS / (asset + entry["extension"])).read_bytes()
    assert hashlib.sha256(source).hexdigest() == entry["sha256"]
    rows = forward_paths(len(entry["nodes"]), entry["edges"], entry["start"])
    # The stepwise verifier expects start 0; relabel the same geometric graph.
    order = [entry["start"]] + [
        i for i in range(len(entry["nodes"])) if i != entry["start"]
    ]
    positions = {old: new for new, old in enumerate(order)}
    expected = time_step_distribution(
        len(order), [(positions[a], positions[b]) for a, b in entry["edges"]]
    )
    actual = {}
    for leaf, _, factors in rows:
        p = F(1)
        for factor in factors:
            p *= factor
        actual[positions[leaf]] = p
    assert actual == expected and sum(actual.values()) == 1
    assert set(entry["destinations"].values()) == {"A", "B", "C", "D", "dead_end"}


@pytest.mark.parametrize(
    "asset,entry",
    [(key, value) for key, value in DATA.items() if value["extension"] == ".png"],
)
def test_each_audited_png_corridor_and_wall_is_visible_in_source_pixels(asset, entry):
    im = Image.open(BytesIO((ASSETS / (asset + ".png")).read_bytes())).convert("RGBA")
    bg = Image.new("RGBA", im.size, "white")
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    open_edges = [(a, b) for a, b in entry["edges"] if a < 20 and b < 20]
    for edges, is_open in [(open_edges, True), (entry["blocked_grid_edges"], False)]:
        for a, b in edges:
            x, y = entry["nodes"][a]
            x2, y2 = entry["nodes"][b]
            length = max(abs(x2 - x), abs(y2 - y))
            run = longest = 0
            for d in range(15, length - 14):
                pixel = im.getpixel(
                    (round(x + (x2 - x) * d / length), round(y + (y2 - y) * d / length))
                )
                run = run + 1 if max(pixel) < 235 else 0
                longest = max(longest, run)
            assert (longest < 8) == is_open, (asset, a, b)


def test_dead_ends_are_not_removed_from_the_sample_space():
    entry = DATA["5d233d45-198f-4499-a026-aa1197d7c29c"]
    probabilities = defaultdict(F)
    for leaf, _, factors in forward_paths(
        len(entry["nodes"]), entry["edges"], entry["start"]
    ):
        p = F(1)
        for factor in factors:
            p *= factor
        probabilities[entry["destinations"][str(leaf)]] += p
    assert probabilities["dead_end"] == F(9, 16)
    assert probabilities["D"] == F(1, 16)
    assert probabilities["D"] / (1 - probabilities["dead_end"]) == F(1, 7)


def test_exit_letter_is_read_from_the_question_instead_of_the_stored_answer():
    case = next(c for c in CASES if c["task"] == "320212")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        'data-math-identifier="D">D<', 'data-math-identifier="B">B<'
    )
    assert condition["html"] != next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert _plan(case, context).answer == "0,25"


@pytest.mark.parametrize("task", ["320212", "322935", "322923", "322925"])
def test_a_changed_diagram_cannot_use_an_old_transcription(task):
    case = next(c for c in CASES if c["task"] == task)
    with pytest.raises(ValueError):
        build_context_repair_plan(
            case["context"],
            condition_asset_bytes=_condition_bytes(case["context"]) + b"\n",
        )
