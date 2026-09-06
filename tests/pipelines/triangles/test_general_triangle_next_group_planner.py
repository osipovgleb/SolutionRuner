import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.triangles.general.next_group_planner import (
    build_repair_plan,
)


def _context(condition_html: str, answer: str = "wrong") -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "html": condition_html,
                    "asset_keys": [],
                },
                {
                    "key": "answer",
                    "section_id": "answer:1",
                    "html": f"<p>{answer}</p>",
                    "asset_keys": [],
                },
            ],
        }
    }


def _solution_html(plan) -> str:
    return next(
        item["value"]["html"]
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )


@pytest.mark.parametrize(
    ("rule", "condition", "parent", "answer", "formula"),
    (
        (
            "general-triangle-27768-bisector-equal-segments-angle",
            "<p>В треугольнике ABC проведена биссектриса AD и AB = AD = CD. "
            "Найдите меньший угол треугольника ABC.</p>",
            '<p>Решение родителя <span data-inline-latex="36^{\\circ}"></span>.</p>',
            "36",
            r"36^{\circ}",
        ),
        (
            "general-triangle-27769-extension-isosceles-angle",
            "<p>В треугольнике ABC угол A равен 100°, угол C равен 13°. "
            "На продолжении AB за B отложен BD, равный BC. Найдите D треугольника BCD.</p>",
            "".join(f'<span data-inline-latex="old{i}"></span>' for i in range(4)),
            "33,5",
            r"180^{\circ}-100^{\circ}-13^{\circ}=67^{\circ}",
        ),
        (
            "general-triangle-27776-bisector-congruent-angle",
            "<p>В треугольнике ABC угол B равен 50°, угол C равен 77°, "
            "AD — биссектриса, E на AB, AE=AC. Найдите BDE.</p>",
            '<span data-inline-latex="old1"></span><span data-inline-latex="old2"></span>',
            "27",
            r"180^{\circ}-50^{\circ}-103^{\circ}=27^{\circ}",
        ),
        (
            "general-triangle-27777-exterior-bisector-isosceles-angle",
            "<p>Угол A равен 17°, угол B равен 46°. CD — биссектриса внешнего угла; "
            "CE=CB. Найдите BDE.</p>",
            '<p><span data-inline-latex="old0"></span></p>'
            '<p><span data-inline-latex="old1"></span></p>'
            '<p><span data-inline-latex="old2"></span><br/>'
            '<span data-inline-latex="old3"></span></p>'
            '<p><span data-inline-latex="old4"></span></p>',
            "29",
            r"\frac{\angle A+\angle B}{2}=31{,}5^{\circ}",
        ),
        (
            "general-triangle-27778-incenter-bisectors-angle",
            "<p>Угол A равен 60°, угол B равен 53°. AD, BE и CF — биссектрисы, "
            "пересекающиеся в точке O. Найдите AOF.</p>",
            '<section data-content-kind="solution">'
            '<span data-inline-latex="old0"></span></section>'
            '<section data-content-kind="solution">'
            '<p><b>Альтернативное решение.</b></p>'
            '<span data-inline-latex="old1"></span>'
            '<span data-inline-latex="old2"></span>'
            '<span data-inline-latex="old3"></span></section>',
            "63,5",
            r"\frac{60^{\circ}}{2}-86{,}5^{\circ}=63{,}5^{\circ}",
        ),
        (
            "general-triangle-27779-orthocenter-altitudes-angle",
            "<p>Угол A равен 21°, угол B равен 11°. AD, BE и CF — высоты, "
            "пересекающиеся в точке O. Найдите AOF.</p>",
            '<span data-inline-latex="old"></span>',
            "11",
            r"\angle AOF=\angle B=11^{\circ}",
        ),
        (
            "general-triangle-500142-altitudes-obtuse-angle",
            "<p>В треугольнике АВС угол А равен 41°, а углы B и C — острые, "
            "BD и CE — высоты, пересекающиеся в точке О. Найдите угол DOE.</p>",
            '<p>Сумма углов четырехугольника равна 360°. Следовательно,</p>'
            '<center><span data-inline-latex="old"></span></center>',
            "139",
            r"360^{\circ}-90^{\circ}-90^{\circ}-41^{\circ}=139^{\circ}",
        ),
        (
            "general-triangle-510796-extended-altitudes-angle",
            "<p>В треугольнике ABC угол A равен 135°. Продолжения высот BD и CE "
            "пересекаются в точке O. Найдите угол DOE.</p>",
            '<p>Угол между прямыми равен углу между перпендикулярами, поэтому</p>'
            '<center><span data-inline-latex="old"></span></center>',
            "45",
            r"180^{\circ}-135^{\circ}=45^{\circ}",
        ),
    ),
)
def test_angle_handlers_adapt_every_parent_formula(
    rule: str, condition: str, parent: str, answer: str, formula: str
) -> None:
    plan = build_repair_plan(
        _context(condition),
        rule=rule,
        parent_solution_html=parent,
        parent_condition_asset_id="parent-condition-image",
    )

    assert plan.answer == answer
    assert formula in _solution_html(plan)
    assert any(
        item["transformation_target_id"] == "asset:image_1"
        for item in plan.transformations
    )


@pytest.mark.parametrize(
    ("rule", "condition", "parent", "answer", "assets", "expected"),
    (
        (
            "general-triangle-317337-midline-small-area-to-total",
            "<p>В треугольнике ABC DE — средняя линия. Площадь треугольника "
            "CDE равна 10. Найдите площадь треугольника ABC.</p>",
            '<p><img data-asset-key="image_1"/></p>'
            '<span data-inline-latex="S_{ABC}=2^{2}\\cdot 38=152"></span>'
            '<p><img data-asset-key="image_2"/></p>'
            '<span data-inline-latex="S_{ABC}=S_{AEC}+S_{CBE}=S_{CDE}+S_{ADE}'
            '+S_{CBE}=4S_{CDE}=4\\cdot 38=152"></span>',
            "40",
            (
                {
                    "asset_key": "image_1",
                    "source_asset_id": "solution-image-1",
                    "url": "/assets/solution-image-1",
                    "alt": "",
                },
                {
                    "asset_key": "image_2",
                    "source_asset_id": "solution-image-2",
                    "url": "/assets/solution-image-2",
                    "alt": "",
                },
            ),
            r"4S_{CDE}=4\cdot 10=40",
        ),
        (
            "general-triangle-319058-midline-trapezoid-area",
            "<p>Площадь треугольника ABC равна 12. DE — средняя линия, "
            "параллельная стороне AB. Найдите площадь трапеции ABDE.</p>",
            '<p><img data-asset-key="image_1"/></p>'
            '<span data-inline-latex="old1"></span><span data-inline-latex="old2"></span>',
            "9",
            (
                {
                    "asset_key": "image_1",
                    "source_asset_id": "solution-image-1",
                    "url": "/assets/solution-image-1",
                    "alt": "",
                },
            ),
            r"S_{\mathrm{трап}}=S_{ABC}-S_{CDE}=12-3=9",
        ),
    ),
)
def test_area_handlers_keep_parent_images_in_solution(
    rule: str,
    condition: str,
    parent: str,
    answer: str,
    assets: tuple[dict[str, str], ...],
    expected: str,
) -> None:
    plan = build_repair_plan(
        _context(condition),
        rule=rule,
        parent_solution_html=parent,
        parent_condition_asset_id="not-a-condition-image",
        parent_solution_assets=assets,
    )

    assert plan.answer == answer
    assert expected in _solution_html(plan)
    solution = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    if rule == "general-triangle-319058-midline-trapezoid-area":
        assert solution["value"]["asset_keys"] == []
        assert 'data-asset-key="image_1"' not in solution["value"]["html"]
        assert any(
            item["value"].get("parent_target_id") == "section:condition:1"
            for item in plan.transformations
        )
    else:
        assert solution["value"]["asset_keys"] == ["image_2"]
        assert 'data-asset-key="image_1"' not in solution["value"]["html"]
        assert any(
            item["value"].get("parent_target_id") == "section:condition:1"
            for item in plan.transformations
        )


def test_requested_solution_layout_changes_are_explicit() -> None:
    parent_27777 = (
        '<p><span data-inline-latex="old0"></span></p>'
        '<p><span data-inline-latex="old1"></span></p>'
        '<p><span data-inline-latex="old2"></span><br/>'
        '<span data-inline-latex="old3"></span></p>'
        '<p><span data-inline-latex="old4"></span></p>'
    )
    plan_27777 = build_repair_plan(
        _context(
            "<p>Угол A равен 17°, угол B равен 46°. CD — биссектриса "
            "внешнего угла; CE=CB. Найдите BDE.</p>"
        ),
        rule="general-triangle-27777-exterior-bisector-isosceles-angle",
        parent_solution_html=parent_27777,
        parent_condition_asset_id="image",
    )
    soup_27777 = BeautifulSoup(_solution_html(plan_27777), "html.parser")
    centered_formulas = soup_27777.find("center").find_all(
        attrs={"data-inline-latex": True}
    )
    assert len(centered_formulas) == 2

    parent_27778 = (
        '<section data-content-kind="solution"><span data-inline-latex="old0"></span></section>'
        '<section data-content-kind="solution"><p><b>Альтернативное решение.</b></p>'
        '<span data-inline-latex="old1"></span><span data-inline-latex="old2"></span>'
        '<span data-inline-latex="old3"></span></section>'
    )
    plan_27778 = build_repair_plan(
        _context(
            "<p>Угол A равен 60°, угол B равен 53°. AD, BE и CF — "
            "биссектрисы, пересекающиеся в точке O. Найдите AOF.</p>"
        ),
        rule="general-triangle-27778-incenter-bisectors-angle",
        parent_solution_html=parent_27778,
        parent_condition_asset_id="image",
    )
    solution_27778 = _solution_html(plan_27778)
    assert "Альтернативное решение" not in solution_27778
    assert solution_27778.count("data-inline-latex") == 3
