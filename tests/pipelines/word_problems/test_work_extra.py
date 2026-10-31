"""Paired rates and the remaining work models extend one existing runner."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_percentages import plan
from test_profile_percentages import (
    test_existing_profile_alias_and_handler_are_reused_without_another_registration as verify_registration,
)
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.word_problems import work_pair_assets as assets
from solution_runner.pipelines.word_problems import work_rate_models as model
from solution_runner.pipelines.word_problems.time_balance import X

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_work_extra.json").read_text()
)
CASES = DATA["cases"]
BOYS = [c for c in CASES if c["group"] == "99616"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    case = case_for(task)
    context = deepcopy(case["context"])
    text = assets.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_six_groups_reuse_the_existing_work_rate_handler(group):
    verify_registration(group)
    assert group["rule"] == "word-work-rate-balance"


@pytest.mark.parametrize(
    "case", [c for c in CASES if c not in BOYS], ids=lambda c: c["task"]
)
def test_text_sources_replay_and_ignore_saved_answers(case):
    verify_source(case)


@pytest.mark.parametrize("case", BOYS, ids=lambda c: c["task"])
def test_boys_reuse_the_inspected_figure_without_generation_or_source_mutation(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    p = plan(case, context)
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert parse_rational(p.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    assert context == original
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999999</p>"
    assert plan(case, context).answer == p.answer
    content = original["normalized_content"]
    additions = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("asset:")
    ]
    assert len(additions) == (0 if case["task"] == "99616" else 1)
    for t in p.transformations:
        if t in additions:
            assert t["operation"] == "add"
            assert t["value"]["asset_id"] == assets.ASSET_ID
            assert t["value"]["url"] == assets.URL
            content["assets"].append(t["value"])
            continue
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        target = next(
            (
                s
                for s in content["sections"]
                if s["transformation_target_id"] == t["transformation_target_id"]
            ),
            None,
        )
        if target is None:
            target = {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": t["transformation_target_id"],
            }
            content["sections"].append(target)
        target.update(t["value"])
    assert plan(case, original).transformations == ()
    soup = BeautifulSoup(p.solution_html, "html.parser")
    sections = soup.select('section[data-content-kind="solution"]')
    assert len(sections) == 3
    assert "Дмитрия Гущина" in sections[0].get_text()
    assert len(sections[0].find_all("img")) == 1
    assert sections[0].img["data-asset-id"] == assets.ASSET_ID
    assert "10+20+24" in str(sections[0])
    assert "кратному" in sections[1].get_text()
    assert "систему" in sections[2].get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_balance_uses_exact_valid_roots_and_requested_output(case):
    _, a = model.calculate(case["context"])
    assert a.balance.domain.contains(a.root) is sp.true
    assert all(d.subs(X, a.root) != 0 for d in a.balance.denominators)
    assert sp.simplify((a.balance.left - a.balance.right).subs(X, a.root)) == 0
    assert a.balance.output.subs(X, a.root) == a.result > 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_foreign_assets_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize("task", ["323852", "504259", "505384", "505405"])
def test_pumps_keep_lcm_double_count_and_attributed_system_in_parent_order(task):
    sections = BeautifulSoup(plan(case_for(task)).solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 3
    assert "кратному" in sections[0].get_text()
    assert "удвоенном" in sections[1].get_text()
    assert "Тимура Алиева" in sections[2]["data-solution-title"]


@pytest.mark.parametrize("task", ["323851", "323941", "504238", "323937"])
def test_tiling_keeps_system_product_and_time_difference_with_same_rate(task):
    sections = BeautifulSoup(plan(case_for(task)).solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 3
    assert "xy=" in str(sections[0]) and "x через y" in sections[0].get_text()
    assert "Умножим новую производительность" in sections[1].get_text()
    assert "Разность планового" in sections[2].get_text()


@pytest.mark.parametrize(
    "task,root,result",
    [("323854", 9, 16), ("324107", 3, 3), ("514023", 18, 27), ("514042", 5, 8)],
)
def test_crews_keep_all_methods_and_distinguish_total_from_new_crew_time(
    task, root, result
):
    _, a = model.calculate(case_for(task)["context"])
    assert a.root == root and a.result == result
    sections = BeautifulSoup(plan(case_for(task)).solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 3
    assert "1/x" in sections[0].get_text()
    assert "сократить" in sections[1].get_text()
    assert "человеко-днях" in sections[2].get_text()
    assert all(
        ("только время" if task == "324107" else "первоначальный этап") in s.get_text()
        for s in sections
    )


def test_integer_hourly_count_selects_between_two_positive_roots():
    _, a = model.calculate(case_for("501213")["context"])
    assert set(a.roots) == {10, sp.Rational(1, 5)}
    assert a.root == 10 and a.result == 2
    html = plan(case_for("501213")).solution_html
    assert "целочисленность" in html and r"n\ne 0{,}2" in html


def test_pump_hour_units_convert_to_minutes_and_name_changes_preserve_roles():
    context = changed("323852", "9 минут", "1 час 30 минут")
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        condition["html"]
        .replace("14 минут", "2 часа 20 минут")
        .replace("18 минут", "3 часа")
    )
    _, a = model.calculate(context)
    assert tuple(a.question.values[k] for k in ("t12", "t23", "t13")) == (90, 140, 180)
    assert a.result == 84
    assert "Переведём время в минуты" in plan(case_for("323852"), context).solution_html
    context = changed("99621", "Петя", "Коля")
    assert plan(case_for("99621"), context).answer == "24"


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99616", "9 часов", "1 час", "positive rate"),
        ("99616", "12 часов", "36 часов", "positive rate"),
        ("99616", "Игорь и Паша", "Игорь и Игорь", "named participants"),
        ("99621", "8 вопросов", "9 вопросов", "lower rate"),
        ("99621", "20 минут", "1 минуту", "one exact rational physical root"),
        ("99621", "позже Вани", "позже Пети", "named participants"),
        ("323851", "на 2 дня", "на 0 дней", "positive work"),
        ("323854", "перешли 8 рабочих", "перешли 4 рабочих", "catch up"),
        ("323854", "перешли 8 рабочих", "перешли 25 рабочих", "catch up"),
        ("501213", "целое количество", "любое количество", "complete work-rate"),
        ("501213", "на две задачи", "на 2,5 задачи", "integer hourly"),
    ],
)
def test_changed_roles_physical_constraints_and_unread_integer_conditions_fail_closed(
    task, old, new, error
):
    with pytest.raises(ValueError, match=error):
        plan(case_for(task), changed(task, old, new))


@pytest.mark.parametrize("value", [{"asset_id": assets.ASSET_ID}, [None], "broken"])
def test_malformed_assets_are_rejected(value):
    context = deepcopy(case_for("99616")["context"])
    context["normalized_content"]["assets"] = value
    with pytest.raises(ValueError, match="list of objects"):
        plan(case_for("99616"), context)


@pytest.mark.parametrize(
    "field,value", [("asset_id", "other"), ("url", "/assets/other"), ("kind", "graph")]
)
def test_only_the_audited_pair_illustration_is_accepted(field, value):
    context = deepcopy(case_for("99616")["context"])
    context["normalized_content"]["assets"][0][field] = value
    with pytest.raises(ValueError, match="exact inspected"):
        plan(case_for("99616"), context)
