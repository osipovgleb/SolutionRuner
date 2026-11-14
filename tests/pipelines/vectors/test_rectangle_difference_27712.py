"""The audited figure fixes the side roles; all available source tasks reuse one rule."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.content_runtime import (
    _context_fingerprint,
    _prepared_record,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.probability.common import UnsupportedCondition
from solution_runner.pipelines.vectors import geometric

ROWS = json.loads(
    (
        Path(__file__).parent / "fixtures/rectangle_difference_27712_sources.json"
    ).read_text()
)
UID = "d18e62d3-2c6d-459a-85d8-4d4639c24609"


def handler():
    return get_handler(get_group_profile("27712").content_rule_key)


def plan(ctx):
    return handler().plan(PlanInput(ctx))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_answers_follow_independent_coordinates_of_the_audited_rectangle(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    assert geometric._EVIDENCE[UID]["short_side"] == "AB"
    ab, ad = sorted(map(sp.Rational, row["sides"]))
    A, D, O = sp.Matrix([0, 0]), sp.Matrix([ad, 0]), sp.Matrix([ad / 2, ab / 2])
    difference = (O - A) - (O - D)
    expected = sp.sqrt(difference.dot(difference))
    p = plan(ctx)
    assert p.answer == str(expected) == row["expected_answer"]
    assert p.condition_html == next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert ctx == original and not handler().diagram_specs(ctx)
    assert (
        r"\overrightarrow{AO}-\overrightarrow{DO}=\overrightarrow{AD}"
        in p.solution_html
    )
    assert "большей" in p.solution_html and "<img" not in p.solution_html
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_source_preparation_is_readonly_and_repeated_plans_converge(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    gateway = Mock(spec_set=["get_problem_context"])
    gateway.get_problem_context.side_effect = lambda identifier: deepcopy(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
    )
    assert (
        record["status"] == "prepared"
        and record["expected_answer"] == row["expected_answer"]
    )
    assert record["input_fingerprint"] == _context_fingerprint(original)
    gateway.get_problem_context.assert_called_once_with(ctx["problem_id"])
    for change in record["transformations"]:
        target = change["transformation_target_id"]
        item = next(
            (
                s
                for s in ctx["normalized_content"]["sections"]
                if s.get("transformation_target_id") == target
            ),
            None,
        )
        if item is None:
            item = {"key": target.split(":")[1], "transformation_target_id": target}
            ctx["normalized_content"]["sections"].append(item)
        item.update(change["value"])
    assert not plan(ctx).transformations
    assert (
        ctx["normalized_content"]["assets"] == original["normalized_content"]["assets"]
    )


def test_an_incorrect_saved_answer_does_not_override_the_audited_side_roles():
    row = next(v for v in ROWS if v["task"] == "60405")
    assert row["sides"] == [25, 46]
    assert plan(row["context"]).answer == "46"
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ctx).answer == "46"


def test_the_existing_exact_source_asset_and_handler_are_reused():
    assert handler().key == "vector-geometric-operations"
    entry = geometric._EVIDENCE[UID]
    path = (
        Path(__file__).parents[3]
        / "src/solution_runner/pipelines/vectors/assets"
        / (UID + entry["extension"])
    )
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == entry["sha256"]
        == "c46ea8e3078fc7ed95e4be6b819407456fe14e9a1ffc071e1270370cf34634b2"
    )


def test_missing_figure_cannot_be_replaced_by_an_assumed_order_of_side_lengths():
    ctx = deepcopy(ROWS[0]["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    condition["html"], condition["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    with pytest.raises(UnsupportedCondition):
        plan(ctx)


def test_changed_asset_bytes_are_rejected_by_the_existing_audit(monkeypatch):
    evidence = deepcopy(geometric._EVIDENCE)
    evidence[UID]["sha256"] = "0" * 64
    monkeypatch.setattr(geometric, "_EVIDENCE", evidence)
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0]["context"])


@pytest.mark.parametrize("mutation", ["asset", "question", "instruction", "zero"])
def test_unknown_figure_question_or_instruction_is_rejected(mutation):
    ctx = deepcopy(ROWS[0]["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "asset":
        ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    elif mutation == "question":
        condition["html"] = condition["html"].replace(
            r"\overrightarrow{DO}", r"\overrightarrow{ZZ}"
        )
    elif mutation == "instruction":
        condition["html"] += "<p>Округлите ответ.</p>"
    else:
        condition["html"] = condition["html"].replace("6 и 8", "0 и 8")
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
