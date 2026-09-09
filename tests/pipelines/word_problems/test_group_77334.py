import pytest

from solution_runner.pipelines.word_problems.group_77334 import (
    UnsupportedCondition,
    build_context_repair_plan,
)


def _context(condition: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [{"key": "condition", "asset_keys": [], "html": f"<p>{condition}</p>"}],
        }
    }


@pytest.mark.parametrize(
    ("condition", "answer", "amount"),
    [
        ("В обменном пункте 1 гривна стоит 3 рубля 70 копеек. Отдыхающие обменяли рубли на гривны и купили 3 кг помидоров по цене 4 гривны за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.", "44", r"12\cdot 3{,}7=44{,}4"),
        ("В обменном пункте 1 гривна стоит 3 рубля 90 копеек. Отдыхающие обменяли рубли на гривны и купили арбуз весом 7 кг по цене 2 гривны за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.", "55", r"14\cdot 3{,}9=54{,}6"),
        ("В обменном пункте 1 гривна стоит 4 рубля 10 копеек. Отдыхающие обменяли рубли на гривны и купили 7 кг апельсинов по цене 11 гривен за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.", "316", r"77\cdot 4{,}1=315{,}7"),
        ("В обменном пункте 1 гривна стоит 4 рубля 10 копеек. Отдыхающие обменяли рубли на гривны и купили 3 кг помидоров по цене 5 гривен за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.", "62", r"15\cdot 4{,}1=61{,}5"),
        ("В обменном пункте 1 гривна стоит 4 рубля 10 копеек. Отдыхающие обменяли рубли на гривны и купили 5 кг помидоров по цене 5 гривен за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.", "103", r"25\cdot 4{,}1=102{,}5"),
    ],
)
def test_calculates_the_five_audited_conditions_exactly(condition: str, answer: str, amount: str) -> None:
    plan = build_context_repair_plan(_context(condition))

    assert plan.answer == answer
    assert amount in plan.solution_html
    assert f"\\approx {answer}" in plan.solution_html
    assert len(plan.transformations) == 2


@pytest.mark.parametrize(
    "condition",
    [
        "В обменном пункте 1 гривна стоит 3 рубля 70 копеек. Отдыхающие обменяли рубли на гривны и купили 3 кг помидоров и 2 кг огурцов по цене 4 гривны за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа.",
        "В обменном пункте 1 гривна стоит 3 рубля 70 копеек. Отдыхающие обменяли рубли на гривны и купили 3 кг помидоров по цене 4 гривны за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите вниз до целого числа.",
    ],
)
def test_rejects_unverified_wording_before_planning_mutations(condition: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(condition))


def test_rejects_non_plain_condition_markup_before_planning_mutations() -> None:
    condition = "В обменном пункте 1 гривна стоит 3 рубля 70 копеек. Отдыхающие обменяли рубли на гривны и купили 3 кг помидоров по цене 4 гривны за 1 кг. Во сколько рублей обошлась им эта покупка? Ответ округлите до целого числа."
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(f"<em>{condition}</em>"))
