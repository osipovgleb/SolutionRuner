from solution_runner.pipelines.word_problems.group_26623 import build_context_repair_plan


def _context(condition: str, answer: str | None = None):
    sections = [{"key": "condition", "html": f"<p>{condition}</p>", "asset_keys": []}]
    if answer is not None:
        sections.append({"key": "answer", "html": f"<p>{answer}</p>", "asset_keys": []})
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": sections}}


def test_monthly_travel_pass_repairs_a_missing_solution_and_answer() -> None:
    plan = build_context_repair_plan(_context(
        "Аня купила проездной билет на месяц и сделала за месяц 45 поездок. Сколько рублей она сэкономила, если проездной билет на месяц стоит 750 рублей, а разовая поездка — 19 рублей?"
    ))

    assert plan.answer == "105"
    assert len(plan.transformations) == 2
    assert "19\\cdot 45=855" in plan.solution_html


def test_monthly_travel_pass_accepts_all_russian_number_forms() -> None:
    plan = build_context_repair_plan(_context(
        "Аня купила проездной билет на месяц и сделала за месяц 30 поездок. Сколько рублей она сэкономила, если проездной билет стоит 207 рублей, а разовая поездка — 20 рублей?",
        "393",
    ))

    assert plan.answer == "393"
    assert len(plan.transformations) == 1
