"""Every reviewed parent method must survive in its original order."""

import pytest
from altitude_source_cases import CASES, PARENTS, plan, section, solution_html
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError


@pytest.mark.parametrize("task", ["27357", "19899", "19901", "19903"])
def test_both_tangent_methods_keep_the_parent_order_and_titles(task):
    case = next(c for c in CASES if c["task"] == task)
    soup = BeautifulSoup(solution_html(plan(case)), "html.parser")
    methods = soup.select('section[data-content-kind="solution"]')
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Приведем другое решение.",
    ]
    formulas = [
        [f["data-inline-latex"] for f in method.select("[data-inline-latex]")]
        for method in methods
    ]
    assert len(formulas[0]) == 1 and len(formulas[1]) == 4
    assert formulas[0][0].startswith(r"BH=CH\tg\angle HCB=CH\tg A=AH\tg^2 A=")
    assert formulas[1][0] == r"\tg A=\frac{CH}{AH}"
    assert formulas[1][2] == r"CH^2=AH\cdot HB"
    assert formulas[1][3].startswith(r"BH=\frac{CH^2}{AH}=")


@pytest.mark.parametrize("alteration", ["metric", "title", "extra_method"])
def test_changed_multiple_parent_methods_are_not_silently_simplified(alteration):
    case = next(c for c in CASES if c["task"] == "19899")
    original = section(PARENTS["27357"]["context"], "solution")["html"]
    if alteration == "metric":
        changed = original.replace(r"CH^{2}=AH\cdot HB", r"CH^{2}=AH+HB")
    elif alteration == "title":
        changed = original.replace("Приведем другое решение.", "Третий способ")
    else:
        changed = (
            original
            + '<section data-content-kind="solution"><p>Ещё способ.</p></section>'
        )
    assert changed != original
    with pytest.raises(ContentPlanError):
        plan(case, parent=changed)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"27268", "27271"}],
    ids=lambda c: c["task"],
)
def test_projection_methods_keep_all_parent_sections_and_their_order(case):
    methods = BeautifulSoup(solution_html(plan(case)), "html.parser").select("section")
    titles = [m["data-solution-title"] for m in methods]
    assert titles == ["Решение"] + ["Альтернативное решение."] * (
        2 if case["group"] == "27268" else 1
    )
    forms = [
        [f["data-inline-latex"] for f in m.select("[data-inline-latex]")]
        for m in methods
    ]
    assert forms[0][0].startswith(r"AH=AC\cos A=")
    assert (
        r"\sqrt{1-\cos^2 A}" in forms[0][0]
        if case["group"] == "27271"
        else r"1-\sin^2 A" in forms[0][0]
    )
    assert forms[1][-1].startswith("AH=AB-HB=")
    if case["group"] == "27268":
        assert forms[2][1].startswith("AC^2=AB^2-BC^2=")
        assert forms[2][-1].startswith(r"AC^2=AB\cdot AH\iff AH=")


@pytest.mark.parametrize("group", ["27268", "27271"])
@pytest.mark.parametrize("alteration", ["omit", "reorder", "formula"])
def test_projection_parent_changes_cannot_drop_or_replace_an_unreviewed_method(
    group, alteration
):
    case = next(c for c in CASES if c["group"] == group and c["task"] != group)
    soup = BeautifulSoup(
        section(PARENTS[group]["context"], "solution")["html"], "html.parser"
    )
    methods = soup.select("section")
    if alteration == "omit":
        methods[-1].decompose()
    elif alteration == "reorder":
        methods[0].insert_before(methods[-1].extract())
    else:
        methods[-1].select_one("[data-inline-latex]")["data-inline-latex"] = "AH=BC+AB"
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize("task", ["27267", "30651", "30661", "30741"])
def test_height_tangent_keeps_both_methods_and_defines_the_positive_leg_variable(task):
    case = next(c for c in CASES if c["task"] == task)
    html = solution_html(plan(case))
    methods = BeautifulSoup(html, "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Приведем другое решение.",
    ]
    first = [n["data-inline-latex"] for n in methods[0].select("[data-inline-latex]")]
    second = [n["data-inline-latex"] for n in methods[1].select("[data-inline-latex]")]
    assert len(first) == 3 and first[:2] == [r"CH=AC\sin A", r"AC=AB\cos A"]
    assert r"1+\tg^2 A" in first[-1]
    assert second[0] == "BC=x" and second[2].startswith(r"AB=\sqrt{AC^2+BC^2}=x")
    assert second[-1].startswith(r"CH=\frac{CB\cdot CA}{AB}=")
    assert "x &gt; 0" in html and r"\alpha" not in html


@pytest.mark.parametrize("alteration", ["omit", "reorder", "formula"])
def test_height_tangent_parent_requires_both_reviewed_methods(alteration):
    case = next(c for c in CASES if c["task"] == "30651")
    soup = BeautifulSoup(
        section(PARENTS["27267"]["context"], "solution")["html"], "html.parser"
    )
    methods = soup.select("section")
    if alteration == "omit":
        methods[-1].decompose()
    elif alteration == "reorder":
        methods[0].insert_before(methods[-1].extract())
    else:
        methods[-1].select("[data-inline-latex]")[-1]["data-inline-latex"] = "CH=CA+CB"
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"27265", "27266"}],
    ids=lambda c: c["task"],
)
def test_hypotenuse_projections_keep_all_three_parent_methods(case):
    html = solution_html(plan(case))
    methods = BeautifulSoup(html, "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Альтернативное решение.",
        "Альтернативное решение.",
    ]
    assert "x &gt; 0" in html
    forms = [
        [f["data-inline-latex"] for f in m.select("[data-inline-latex]")]
        for m in methods
    ]
    assert r"1+\tg^2 A" in forms[0][0]
    if case["group"] == "27265":
        assert "Корень x = 0 не подходит" in html
        assert r"CH^2=AH\cdot HB" in forms[1] and forms[2][0] == "AH=x"
    else:
        assert forms[1][0] == "BH=x" and r"AC^2+BC^2=AB^2" in forms[2][2]


@pytest.mark.parametrize("task", ["27273", "30983", "30985", "30987"])
def test_complementary_angle_method_extends_the_thirty_degree_case_without_invented_angles(
    task,
):
    case = next(c for c in CASES if c["task"] == task)
    methods = BeautifulSoup(solution_html(plan(case)), "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Приведем другое решение.",
    ]
    second = str(methods[1])
    assert (
        ("угол B равен 30°" in second and r"\frac{BC}{2}" in second)
        if task == "27273"
        else ("30°" not in second and r"\sin B=\cos A=" in second)
    )


@pytest.mark.parametrize("group", ["27265", "27266", "27273"])
def test_unreviewed_changes_to_additional_projection_arguments_are_rejected(group):
    case = next(c for c in CASES if c["group"] == group and c["task"] != group)
    soup = BeautifulSoup(
        section(PARENTS[group]["context"], "solution")["html"], "html.parser"
    )
    soup.select("section")[-1].decompose()
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize("group", ["27265", "27266"])
@pytest.mark.parametrize("alteration", ["reorder", "formula"])
def test_hypotenuse_parent_methods_require_the_reviewed_order_and_equations(
    group, alteration
):
    case = next(c for c in CASES if c["group"] == group and c["task"] != group)
    soup = BeautifulSoup(
        section(PARENTS[group]["context"], "solution")["html"], "html.parser"
    )
    methods = soup.select("section")
    if alteration == "reorder":
        methods[0].insert_before(methods[-1].extract())
    else:
        methods[-1].select("[data-inline-latex]")[-1]["data-inline-latex"] = "AH=AB+BH"
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize("alteration", ["angle", "extra_instruction"])
def test_unreviewed_plaintext_complementary_argument_is_not_ignored(alteration):
    case = next(c for c in CASES if c["task"] == "30983")
    html = section(PARENTS["27273"]["context"], "solution")["html"]
    changed = (
        html.replace("60°", "45°")
        if alteration == "angle"
        else html.replace("</section>", "<p>Удвойте ответ.</p></section>")
    )
    with pytest.raises(ContentPlanError):
        plan(case, parent=changed)
