"""Annual capitalization, positive factors and precise source replay."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_profile_percentages import (
    test_existing_profile_alias_and_handler_are_reused_without_another_registration as verify_registration,
)
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.word_problems import compound_deposit as model
from solution_runner.pipelines.word_problems import math_common

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_deposits.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_deposit_rule_is_registered_in_the_existing_domain(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_source_replays_compute_answers_without_saved_answer_dependency(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.capital * a.factor**2 - a.capital * a.factor == a.difference
    assert a.factor > 1 and a.result == 100 * (a.factor - 1)
    assert len(a.roots) == 2 and sum(bool(root > 0) for root in a.roots) == 1


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_assets_cannot_be_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("7700 рублей", "0 рублей", "positive principal"),
        ("847 рублей", "-847 рублей", "positive principal"),
        ("847 рублей", "0 рублей", "positive principal"),
        ("847 рублей", "848 рублей", "exact rational"),
        ("раз в год", "раз в месяц", "complete"),
        ("такой же вклад", "другой вклад", "complete"),
        ("Ровно через год", "Ровно через два года", "complete"),
    ],
)
def test_changed_timing_and_nonphysical_data_fail_closed(old, new, error):
    case = CASES[0]
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    with pytest.raises(ValueError, match=error):
        model.calculate(context)
