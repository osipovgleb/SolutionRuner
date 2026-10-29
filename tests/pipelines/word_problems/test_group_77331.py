from copy import deepcopy

import pytest

from solution_runner.pipelines.word_problems.group_77331 import UnsupportedCondition, build_context_repair_plan


def context(before=53, after=8, rubles=2, kopecks=50, *, alternate=False):
    prefix = f"На счету Машиного мобильного телефона было {before} рубля, а после разговора с Леной осталось {after} рублей. "
    price = f"{rubles} рубля {kopecks} копеек"
    ending = (
        f"Известно, что разговор длился целое число минут, а одна минута разговора стоит {price}. Сколько минут длился разговор с Леной?"
        if alternate else f"Сколько минут длился разговор с Леной, если одна минута разговора стоит {price}?"
    )
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [],
        "sections": [{"key": "condition", "html": f"<p>{prefix}{ending}</p>", "asset_keys": []}]}}


@pytest.mark.parametrize("before,after,rubles,kopecks,answer", [(53, 8, 2, 50, "18"), (82, 40, 3, 50, "12"), (79, 40, 1, 50, "26"), (56, 21, 2, 50, "14"), (3, 0, 0, 25, "12")])
@pytest.mark.parametrize("alternate", [False, True])
def test_exact_duration_and_independent_solution(before, after, rubles, kopecks, answer, alternate):
    source = context(before, after, rubles, kopecks, alternate=alternate)
    original = deepcopy(source)
    plan = build_context_repair_plan(source)
    assert source == original
    assert plan.answer == answer
    assert len(plan.transformations) == 2
    assert plan.solution_html.count("data-inline-latex") == 5
    assert "Маше" in plan.solution_html


def test_preserves_editorial_solution_and_correct_answer():
    source = context()
    source["normalized_content"]["sections"] += [
        {"key": "solution", "html": "<p>Авторское решение</p>", "asset_keys": []},
        {"key": "answer", "html": "<p>18</p>", "asset_keys": []},
    ]
    assert build_context_repair_plan(source).transformations == ()


@pytest.mark.parametrize("before,after,rubles,kopecks", [(53, 8, 2, 100), (8, 53, 2, 50), (53, 53, 2, 50), (53, 8, 0, 0), (53, 8, 2, 51)])
def test_rejects_invalid_or_nonintegral_data(before, after, rubles, kopecks):
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(before, after, rubles, kopecks))


@pytest.mark.parametrize("old,new", [("с Леной,", "с Вовой,"), ("одна минута", "две минуты"), ("Машиного", "Неизвестного"), ("</p>", " Дополнительная плата 5 рублей.</p>")])
def test_rejects_unverified_wording(old, new):
    source = context()
    source["normalized_content"]["sections"][0]["html"] = source["normalized_content"]["sections"][0]["html"].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(source)


def test_rejects_assets():
    source = context()
    source["normalized_content"]["assets"] = [{"asset_key": "image_1"}]
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(source)


@pytest.mark.parametrize("owner,dative", [("Юлиного", "Юле"), ("Надиного", "Наде"), ("Наташиного", "Наташе"), ("Жениного", "Жене")])
def test_name_and_singular_balance_variants(owner, dative):
    source = context(71, 47, 1, 50)
    condition = source["normalized_content"]["sections"][0]
    condition["html"] = condition["html"].replace("Машиного", owner).replace("было 71 рубля", "был 71 рубль")
    plan = build_context_repair_plan(source)
    assert plan.answer == "16"
    assert dative in plan.solution_html
    assert r"16\text{ мин.}" in plan.solution_html


def test_repairs_wrong_source_answer_without_changing_condition():
    source = context(62, 26, 1, 50)
    source["normalized_content"]["sections"].append({"key": "answer", "html": "<p>1</p>", "asset_keys": []})
    plan = build_context_repair_plan(source)
    assert plan.answer == "24"
    assert any(t["transformation_target_id"] == "section:answer" and t["value"]["html"] == "<p>24</p>" for t in plan.transformations)
