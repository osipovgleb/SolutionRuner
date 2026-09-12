import pytest

from solution_runner.pipelines.word_problems.common import UnsupportedCondition
from solution_runner.pipelines.word_problems.group_323514 import build_context_repair_plan


def _context(condition: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [{"key": "condition", "asset_keys": [], "html": f"<p>{condition}</p>"}]}}


@pytest.mark.parametrize(("condition", "answer"), [
    ("Одного рулона обоев хватает для оклейки полосы от пола до потолка шириной 1,6 м. Какое наименьшее количество рулонов обоев нужно купить для оклейки прямоугольной комнаты размерами 2,3 м на 4,1 м?", "8"),
    ("Одного рулона обоев хватает для оклейки полосы от пола до потолка шириной 1,4 м. Сколько рулонов обоев нужно купить для оклейки прямоугольной комнаты размерами 3,2 м на 2,8 м?", "9"),
])
def test_wallpaper_rolls_are_rounded_up(condition: str, answer: str) -> None:
    plan = build_context_repair_plan(_context(condition))

    assert plan.answer == answer
    assert len(plan.transformations) == 2


def test_rejects_another_ceiling_problem() -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context("Для ремонта нужно купить рулоны обоев шириной 1,6 м."))
