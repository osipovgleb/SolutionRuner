from solution_runner.pipelines.equations.algebraic_conjugate_reciprocal_linear_tail import build_context_repair_plan


def test_reduces_reciprocal_difference_then_substitutes():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="(9b^{2}-49)(\\frac{1}{3b-7}-\\frac{1}{3b+7})+b-13"></span><span data-inline-latex="b=345"></span></p>'}],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "346"
    html = plan.transformations[0]["value"]["html"]
    assert "\\frac{14}{9b^{2}-49}" in html
    assert "14+b-13=b+1" in html
    assert "1\\cdot(345)+1=346" in html
