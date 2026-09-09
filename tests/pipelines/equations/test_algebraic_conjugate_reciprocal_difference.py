from solution_runner.pipelines.equations.algebraic_conjugate_reciprocal_difference import build_context_repair_plan


def test_reduces_reciprocal_difference_before_substitution():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="a(36a^{2}-25)(\\frac{1}{6a+5}-\\frac{1}{6a-5})"></span><span data-inline-latex="a=36{,}7"></span></p>'}],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "-367"
    html = plan.transformations[0]["value"]["html"]
    assert "Приведём дроби в скобках к общему знаменателю" in html
    assert "-\\frac{10}{36a^{2}-25}" in html
    assert "-10\\cdot(36{,}7)=-367" in html


def test_reads_a_value_written_as_plain_html_text():
    context = {
        "normalized_content": {
            "assets": [], "format": "teacherhelper-normalized", "schema_version": 3,
            "sections": [{"key": "condition", "html": '<p><span data-inline-latex="a(36a^{2}-25)(\\frac{1}{6a+5}-\\frac{1}{6a-5})"></span> при <i>a</i> = 36,7.</p>'}],
        }
    }

    assert build_context_repair_plan(context).answer == "-367"
