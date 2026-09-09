from solution_runner.pipelines.equations.algebraic_complementary_affine_sum import build_context_repair_plan


def test_builds_two_detailed_solutions_and_repairs_answer():
    context = {
        "normalized_content": {
            "assets": [],
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": [
                {
                    "key": "condition",
                    "html": '<p><span data-inline-latex="p(x-7)+p(13-x)"></span><span data-inline-latex="p(x)=2x+1"></span></p>',
                }
            ],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "14"
    html = plan.transformations[0]["value"]["html"]
    assert "Раскроем скобки" in html
    assert "p(-6)+p(12)" in html
    assert "Приведём другое решение" in html
    assert "x=1" in html
    assert "p(-6)=2\\cdot(-6)+1=-11" in html
    assert "p(12)=2\\cdot(12)+1=25" in html
