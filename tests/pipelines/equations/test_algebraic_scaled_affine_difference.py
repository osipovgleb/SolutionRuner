from solution_runner.pipelines.equations.algebraic_scaled_affine_difference import build_context_repair_plan


def test_builds_detailed_main_and_alternative_solutions():
    context = {
        "normalized_content": {
            "assets": [],
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="2p(x-7)-p(2x)"></span><span data-inline-latex="p(x)=x-3"></span></p>'}],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "-17"
    html = plan.transformations[0]["value"]["html"]
    assert "Раскроем внутренние скобки" in html
    assert "p(-6)" in html and "p(2)" in html
    assert "2\\cdot(-9)-(-1)=-17" in html
    assert "p(x-7)=(x-7)-3" in html


def test_supports_a_positive_shift():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="2p(x+5)-p(2x)"></span><span data-inline-latex="p(x)=2x-6"></span></p>'}],
        }
    }

    assert build_context_repair_plan(context).answer == "14"
