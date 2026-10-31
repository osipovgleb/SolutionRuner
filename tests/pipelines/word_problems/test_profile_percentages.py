"""Replay the existing six percentage runners against profile-catalogue inputs."""

import json
from copy import deepcopy
from html import escape
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.word_problems.common import require_content

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_percentages.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def plan(case, context=None):
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    return handler.plan(PlanInput(case["context"] if context is None else context))


def changed(task, old, new):
    case = sample(task)
    context = deepcopy(case["context"])
    text = require_content(context, allow_inline_latex=True)[-1]
    assert old in text
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = "<p>" + escape(text.replace(old, new)) + "</p>"
    return plan(case, context)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["source_key"])
def test_existing_profile_alias_and_handler_are_reused_without_another_registration(
    group,
):
    p = get_group_profile(group["key"])
    assert p.source_group_id == group["uuid"]
    assert p.snapshot_theme_id == group["theme_uuid"]
    assert p.group_order_index == group["order"]
    assert p.content_rule_key == group["rule"]
    assert p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert p.category_key == "11"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes(
    case,
):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    result = plan(case, context)
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    assert context == original
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999999</p>"
    assert plan(case, context).answer == result.answer
    context = deepcopy(original)
    for t in result.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        section = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        section.update(t["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_assets_fail_closed(case, mode):
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if mode in ["leading", "trailing"]:
        condition = next(s for s in content["sections"] if s["key"] == "condition")
        extra = "<p>Выберите другой способ начисления процентов.</p>"
        condition["html"] = (
            extra + condition["html"]
            if mode == "leading"
            else condition["html"] + extra
        )
    elif mode == "asset":
        content["assets"] = [{"asset_id": "foreign", "asset_key": "image_1"}]
    else:
        next(s for s in content["sections"] if s["key"] == "solution")["asset_keys"] = [
            "foreign"
        ]
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize("task", ["99566", "99567", "99568"])
def test_both_parent_methods_remain_in_the_prepared_solution(task):
    result = plan(sample(task))
    soup = BeautifulSoup(result.solution_html, "html.parser")
    assert len(soup.select('section[data-content-kind="solution"]')) == 2
    if task == "99566":
        assert "ЛАЙФХАК" in result.solution_html
    elif task == "99568":
        assert "М+Ж+Д=100" in result.solution_html
        assert "Вычтем первое уравнение из второго" in result.solution_html


@pytest.mark.parametrize("task,tables", [("99565", 1), ("99570", 2)])
def test_existing_parent_tables_are_retained(task, tables):
    html = plan(sample(task)).solution_html
    assert len(BeautifulSoup(html, "html.parser").find_all("table")) == tables


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99565", "В 2008 году", "В 2011 году", "chronological"),
        ("99566", "на 4% дешевле", "на 144% дешевле", "cannot exceed"),
        ("99567", "на 8%", "на 100%", "positive"),
        ("99567", "пять таких", "четыре таких", "dearer"),
        ("99568", "на 67%", "на 99%", "cannot be negative"),
        ("99569", "15 842", "20 000", "positive integer percent"),
        ("99570", "Борису", "Валерию", "unambiguously"),
    ],
)
def test_invalid_chronology_prices_income_and_recipient_are_not_guessed(
    task, old, new, error
):
    with pytest.raises(ValueError, match=error):
        changed(task, old, new)


@pytest.mark.parametrize(
    "recipient,amount",
    [
        ("Мите", "140000"),
        ("Антону", "210000"),
        ("Гоше", "120000"),
        ("Борису", "530000"),
    ],
)
def test_profit_answer_is_for_the_founder_actually_asked_about(recipient, amount):
    result = changed("99570", "Борису", recipient)
    assert result.answer == amount
    assert "<b>" + recipient + "</b> причитается" in result.solution_html


def test_ambiguous_founder_names_are_refused():
    with pytest.raises(ValueError, match="unambiguously"):
        changed("99570", "Гоша", "Борис")


def test_zero_remaining_income_is_valid_and_one_hundred_percent_loss_is_nonnegative():
    assert changed("99568", "на 67%", "на 94%").answer == "0"
    assert changed("99566", "на 4% дешевле", "на 100% дешевле").answer == "100"
