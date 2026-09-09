from solution_runner.pipelines.equations.algebraic_conjugate_product_value import build_context_repair_plan


def test_uses_the_difference_of_squares_before_substitution():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="(7x-13)(7x+13)-49x^{2}+6x+22"></span><span data-inline-latex="x=80"></span></p>'}],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "333"
    html = plan.transformations[0]["value"]["html"]
    assert "a^{2}-b^{2}=(a-b)(a+b)" in html
    assert "49x^{2}-169-49x^{2}+6x+22=6x-147" in html
    assert "6\\cdot(80)-147=333" in html


def test_supports_an_expression_without_a_linear_term():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="(8x-3)(8x+3)-64x^{2}+35"></span><span data-inline-latex="x=140"></span></p>'}],
        }
    }

    assert build_context_repair_plan(context).answer == "26"


def test_supports_an_implicit_linear_coefficient():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="(3x-9)(3x+9)-9x^{2}+x-2"></span><span data-inline-latex="x=150"></span></p>'}],
        }
    }

    assert build_context_repair_plan(context).answer == "67"
