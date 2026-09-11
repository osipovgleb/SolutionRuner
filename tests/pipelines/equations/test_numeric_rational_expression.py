from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.numeric_rational_expression import (
    build_context_repair_plan,
)


def _context(formula: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "title": "Условие",
                    "section_id": "condition:1",
                    "html": f'<p><span data-inline-latex="{formula}"></span></p>',
                    "asset_keys": [],
                },
                {
                    "key": "answer",
                    "title": "Ответ",
                    "section_id": "answer:1",
                    "html": "<p></p>",
                    "asset_keys": [],
                },
            ],
        }
    }


def test_numeric_rational_expression_handles_all_registered_shapes() -> None:
    cases = (
        (r"(\frac{3}{4}+2\frac{3}{8})\cdot25{,}6", "80"),
        (r"(2\frac{4}{7}-1{,}2)\cdot5\frac{5}{6}", "8"),
        (r"(2\frac{4}{7}-2{,}5)\colon\frac{1}{70}", "5"),
        (r"(\frac{19}{8}+\frac{11}{12})\colon\frac{5}{48}", "31,6"),
        (r"(\frac{14}{11}+\frac{17}{10})\cdot\frac{11}{15}", "2,18"),
    )
    for formula, answer in cases:
        plan = build_context_repair_plan(_context(formula))
        assert plan.answer == answer
        assert len(plan.transformations) == 2


def test_numeric_rational_expression_handles_the_remaining_base_ege_forms() -> None:
    cases = (
        (r"1\frac{1}{12}\colon(1\frac{13}{18}-2\frac{5}{9})", "-1,3"),
        (r"\frac{14}{15}\colon\frac{7}{3}-0{,}5", "-0,1"),
        (r"\frac{3}{2}\colon(1+\frac{1}{9})", "1,35"),
        (r"\frac{1}{\frac{1}{9}-\frac{1}{12}}", "36"),
        (r"\frac{3{,}1-5{,}7}{2{,}5}", "-1,04"),
        (r"6{,}6-5\cdot(-3{,}5)", "24,1"),
        (r"28\cdot(\frac{2}{7}-\frac{3}{14}-\frac{5}{28})", "-3"),
    )
    for formula, answer in cases:
        assert build_context_repair_plan(_context(formula)).answer == answer


def test_numeric_rational_expression_profiles_cover_profile_base_and_oge() -> None:
    profiles = all_group_profiles()
    for key in (
        "26900",
        "77387",
        "77389",
        "ege-base-26900",
        "ege-base-77387",
        "ege-base-77389",
        "oge-314288",
        "oge-333111",
    ):
        assert profiles[key].content_rule_key == "numeric-rational-expression-mixed-decimal"
