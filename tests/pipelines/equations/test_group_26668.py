import pytest

from solution_runner.pipelines.equations.group_26668 import (
    UnsupportedCondition,
    build_context_repair_plan,
)


def _context(formula: str, choice: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "asset_keys": [],
                    "html": (
                        "<p>Най­ди­те ко­рень урав­не­ния: "
                        f'<span data-inline-latex="{formula}"></span>. '
                        f"Если уравнение имеет более одного корня, укажите {choice} из них.</p>"
                    ),
                }
            ],
        }
    }


@pytest.mark.parametrize(
    ("formula", "choice", "answer", "has_choice_prose"),
    [
        (r"\sqrt{-72-17x}=-x", "меньший", "-9", True),
        (r"\sqrt{-63-16x}=-x", "меньший", "-9", True),
        (r"\sqrt{-72-17x}=-x", "больший", "-8", True),
        (r"\sqrt{-72+17x}=x", "меньший", "8", True),
        (r"\sqrt{72+21x}=-x", "меньший", "-3", False),
        (r"\sqrt{72+21x}=x", "больший", "24", False),
    ],
)
def test_adapts_parent_template_and_honours_the_child_root_choice(
    formula: str, choice: str, answer: str, has_choice_prose: bool
) -> None:
    plan = build_context_repair_plan(_context(formula, choice))

    assert plan.answer == answer
    assert r"\begin{cases}" in plan.solution_html
    assert (
        f"{choice.capitalize()} корень равен {answer}" in plan.solution_html
    ) is has_choice_prose
    assert (r"\iff \left[\begin{aligned}" in plan.solution_html) is has_choice_prose


def test_rejects_non_integral_quadratic_roots() -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(r"\sqrt{-1-3x}=-x", "меньший"))


def test_omits_root_selection_prose_and_final_set_for_one_admissible_root() -> None:
    plan = build_context_repair_plan(_context(r"\sqrt{9-8x}=-x", "меньший"))

    assert plan.answer == "-9"
    assert r"\iff x=-9" in plan.solution_html
    assert "Меньший корень" not in plan.solution_html


@pytest.mark.parametrize(
    ("formula", "choice", "answer"),
    [
        (r"\sqrt{34-3x}=x-2", "меньший", "6"),
        (r"\sqrt{1+x}=x+1", "меньший", "-1"),
        (r"\sqrt{1+x}=x+1", "больший", "0"),
    ],
)
def test_shifted_right_side_filters_roots_including_zero(formula, choice, answer):
    assert build_context_repair_plan(_context(formula, choice)).answer == answer


def test_equation_without_selector_must_have_one_admissible_root():
    context = _context(r"\sqrt{34-3x}=x-2", "меньший")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Решите уравнение <span data-inline-latex="\\sqrt{34-3x}=x-2"></span>.</p>'
    )
    assert build_context_repair_plan(context).answer == "6"
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Решите уравнение <span data-inline-latex="\\sqrt{-6+5x}=x"></span>.</p>'
    )
    with pytest.raises(UnsupportedCondition, match="selector"):
        build_context_repair_plan(context)
