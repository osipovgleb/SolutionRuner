import pytest

from solution_runner.pipelines.equations.group_511751 import (
    UnsupportedCondition,
    build_context_repair_plan,
)


def _context(formula: str, *, answer: str = "", solution: str = "") -> dict:
    sections = [{
        "key": "condition", "section_id": "condition:1",
        "transformation_target_id": "section:condition:1", "asset_keys": [],
        "html": f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>.</p>',
    }]
    if answer:
        sections.append({
            "key": "answer", "section_id": "answer:1",
            "transformation_target_id": "section:answer:1", "asset_keys": [],
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
        })
    if solution:
        sections.append({
            "key": "solution", "section_id": "solution:1",
            "transformation_target_id": "section:solution:1", "asset_keys": [],
            "html": solution,
        })
    return {"normalized_content": {
        "format": "teacherhelper-normalized", "schema_version": 3,
        "assets": [], "sections": sections,
    }}


@pytest.mark.parametrize(("formula", "answer"), [
    (r"\frac{1}{\sqrt{x}}=\frac{1}{5}", "25"),
    (r"\frac{1}{\sqrt{x}}=\frac{1}{7}", "49"),
    (r"\frac{1}{\sqrt{x}}=\frac{1}{8}", "64"),
])
def test_repairs_reciprocal_square_root_equations_in_parent_style(formula: str, answer: str) -> None:
    plan = build_context_repair_plan(_context(formula))
    assert plan.answer == answer
    assert f"\\sqrt{{x}}={int(int(answer) ** .5)}\\iff x={answer}" in plan.solution_html
    assert {item["transformation_target_id"] for item in plan.transformations} == {
        "section:solution", "section:answer",
    }


def test_plan_converges_when_parent_style_solution_and_equivalent_answer_exist() -> None:
    formula = r"\frac{1}{\sqrt{x}}=\frac{1}{5}"
    initial = build_context_repair_plan(_context(formula))
    assert initial.answer == "25"
    assert build_context_repair_plan(_context(formula, answer="25", solution=initial.solution_html)).transformations == ()


@pytest.mark.parametrize("formula", [
    r"\frac{2}{\sqrt{x}}=\frac{1}{5}",
    r"\frac{1}{\sqrt{x}}=\frac{2}{5}",
    r"\frac{1}{\sqrt{x+1}}=\frac{1}{5}",
])
def test_unknown_forms_fail_closed(formula: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(formula))
