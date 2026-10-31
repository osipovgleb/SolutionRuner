"""Regression coverage for the five unsupported tasks in group 1001."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from solution_runner.pipelines.probability.common import require_content
from solution_runner.pipelines.probability.counting import build_context_repair_plan, solve


CASES = json.loads((Path(__file__).parent / "fixtures/group_1001_repairs.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["source_problem_id"])
def test_live_television_tasks_compute_complements_without_using_saved_answers(case):
    context = deepcopy(case)
    _, _, answer, _, _ = require_content(context)
    expected = {"1006": "0,8", "1007": "0,9", "1008": "0,75", "1009": "0,875", "1010": "0,6"}[case["source_problem_id"]]
    answer["html"] = "<p>1234567</p>"
    original = deepcopy(context)
    plan = build_context_repair_plan(context)
    assert plan.answer == expected
    assert context == original
    assert "вычтем" in plan.solution_html.lower()
    assert any(t["value"]["html"].find(expected) >= 0 for t in plan.transformations)


@pytest.mark.parametrize("replacement", [
    ("новости не идут", "новости идут"),
    ("новости не идут", "клипы не идут"),
    ("Маша попадет", "Люба попадет"),
    ("девяти", "50"),
    ("сорока пяти", "0"),
    ("случайном канале", "любимом канале"),
])
def test_changed_event_or_invalid_counts_fail_closed(replacement):
    text = require_content(CASES[0])[-1]
    assert replacement[0] in text
    with pytest.raises(ValueError):
        solve(text.replace(*replacement))


def test_extra_instruction_fails_closed():
    text = require_content(CASES[0])[-1]
    with pytest.raises(ValueError):
        solve(text + " В ответе запишите удвоенную вероятность.")
