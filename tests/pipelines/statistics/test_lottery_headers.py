"""Lottery column units must be read without weakening distribution checks."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from solution_runner.pipelines.statistics.moments import build_context_repair_plan


CONTEXT = json.loads(
    (Path(__file__).parent / "fixtures/lottery_509368.json").read_text()
)["context"]


def test_lottery_with_ruble_column_header_computes_from_the_table():
    context = deepcopy(CONTEXT)
    original = deepcopy(context)
    answer = next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")
    answer["html"] = "<p>999</p>"
    plan = build_context_repair_plan(context)
    assert plan.answer == "92,5"
    assert r"E(X)=\frac{245}{2}" in plan.solution_html
    assert r"\Delta=215-\frac{245}{2}" in plan.solution_html
    assert next(s for s in context["normalized_content"]["sections"] if s["key"] == "condition") == next(
        s for s in original["normalized_content"]["sections"] if s["key"] == "condition"
    )


@pytest.mark.parametrize("old,new", [
    ("руб.", "коп."),
    ("985", "986"),
    ("985", "-1"),
    ("100</td>", "-100</td>"),
])
def test_lottery_still_rejects_other_units_and_invalid_distribution(old, new):
    context = deepcopy(CONTEXT)
    condition = next(s for s in context["normalized_content"]["sections"] if s["key"] == "condition")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    original = deepcopy(context)
    with pytest.raises(ValueError):
        build_context_repair_plan(context)
    assert context == original
