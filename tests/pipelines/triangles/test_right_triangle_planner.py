"""Protect deterministic repairs for sine-based right-triangle source tasks."""

from __future__ import annotations

from html import unescape
import re

import pytest

from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
    build_altitude_repair_plan,
    build_repair_plan,
    build_tangent_bc_repair_plan,
    build_universal_repair_plan,
)
from solution_runner.pipelines.triangles.right.runtime import run_manifest
from solution_runner.pipelines.triangles.right.runtime import (
    _build_content_plan,
)


PARENT_ASSET_ID = "8f8988bb-fa85-47a8-be0e-75edaf5a7604"


def _solution_formulas(plan: object) -> list[str]:
    """Return decoded centered calculation rows from the planned solution."""

    transformation = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    html = unescape(transformation["value"]["html"])
    return [
        formula
        for block in re.findall(r"<center>.*?</center>", html, re.DOTALL)
        for formula in re.findall(r'data-inline-latex="([^"]+)"', block)
    ]


def _context(*, answer: str, solution_html: str = "", asset_id: str | None = None) -> dict:
    """Return a complete minimal schema-v3 transformation context fixture."""

    condition = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол '
        '<var data-math-identifier="C">C</var> равен 90°, '
        '<span data-inline-latex="\\sin A=\\frac{3}{5}"></span>, '
        '<span data-inline-latex="AC=4"></span>. Найдите '
        '<var data-math-identifier="AB">AB</var>.</p>'
    )
    assets = []
    if asset_id is not None:
        assets.append(
            {
                "asset_key": "image_1",
                "asset_id": asset_id,
                "url": f"/assets/{asset_id}",
                "kind": "ordinary_image",
                "alt": "",
            }
        )
    sections = [
        {"key": "condition", "section_id": "condition:1", "html": condition},
        {
            "key": "answer",
            "section_id": "answer:1",
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
        },
    ]
    if solution_html:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "html": solution_html,
            }
        )
    return {
        "problem_id": "problem-1",
        "source_problem_id": "4583",
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": sections,
            "assets": assets,
        },
    }


def _altitude_context(
    *,
    answer: str,
    solution_html: str = "",
    asset_id: str | None = None,
) -> dict:
    """Return one strict altitude-condition context for planner tests."""

    context = _context(
        answer=answer,
        solution_html=solution_html,
        asset_id=asset_id,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, CH — высота, '
        '<span data-inline-latex="AB=13"></span>, '
        '<span data-inline-latex="\\tg A=\\frac{1}{5}"></span>. '
        'Найдите AH.</p>'
    )
    return context


def _elementary_context(condition_html: str, *, answer: str) -> dict:
    """Return a schema-v3 task for an elementary right-triangle content rule."""

    context = _context(answer=answer)
    context["normalized_content"]["sections"][0]["html"] = condition_html
    return context


@pytest.mark.parametrize(
    ("content_rule_key", "condition_html", "answer", "formulas"),
    [
        (
            "right-triangle-leg-hypotenuse-area",
            "<p>Найдите площадь прямоугольного треугольника, если его катет "
            "и гипотенуза равны соответственно 36 и 39.</p>",
            "270",
            [
                r"b=\sqrt{39^{2}-36^{2}}=15",
                r"S=\frac{1}{2}\cdot36\cdot15=270",
            ],
        ),
        (
            "right-triangle-area-leg-difference",
            "<p>Площадь прямоугольного треугольника равна 2. Один из его "
            "катетов на 3 больше другого. Найдите меньший катет.</p>",
            "1",
            [
                r"\frac{1}{2}x(x+3)=2\iff x(x+3)=4\iff x^{2}+3x-4=0"
                r"\iff \begin{cases}\left[\begin{aligned}x=1\\x=-4"
                r"\end{aligned}\right.\\x\gt 0\end{cases}\iff x=1",
            ],
        ),
        (
            "right-triangle-acute-angle-difference",
            "<p>Один острый угол прямоугольного треугольника на 38° больше "
            "другого. Найдите больший острый угол. Ответ дайте в градусах.</p>",
            "64",
            [
                r"\begin{cases}\angle A-\angle B=38^{\circ}\\"
                r"\angle A+\angle B=90^{\circ}\end{cases}"
                r"\iff \begin{cases}\angle A=64^{\circ}\\"
                r"\angle B=26^{\circ}\end{cases}",
            ],
        ),
        (
            "right-triangle-acute-angle-difference",
            '<p>Один острый угол прямоугольного треугольника на '
            '<span data-inline-latex="1^{\\circ}"></span> больше другого. '
            "Найдите больший острый угол.</p>",
            "45,5",
            [
                r"\begin{cases}\angle A-\angle B=1^{\circ}\\"
                r"\angle A+\angle B=90^{\circ}\end{cases}"
                r"\iff \begin{cases}\angle A=45{,}5^{\circ}\\"
                r"\angle B=44{,}5^{\circ}\end{cases}",
            ],
        ),
        (
            "right-triangle-acute-angle-difference",
            '<p>Один острый угол прямоугольного треугольника на '
            '<span data-inline-latex="6^{\\circ}"></span> больше другого. '
            "Найдите больший острый угол.</p>",
            "48",
            [
                r"\begin{cases}\angle A-\angle B=6^{\circ}\\"
                r"\angle A+\angle B=90^{\circ}\end{cases}"
                r"\iff \begin{cases}\angle A=48^{\circ}\\"
                r"\angle B=42^{\circ}\end{cases}",
            ],
        ),
        (
            "right-triangle-acute-angle-ratio",
            '<p>Один острый угол прямоугольного треугольника в '
            '<span data-inline-latex="\\frac{19}{11}"></span> раза больше '
            "другого. Найдите больший острый угол.</p>",
            "57",
            [
                r"11x+19x=90^{\circ}\iff30x=90^{\circ}\iff x=3^{\circ}",
                r"19x=19\cdot3^{\circ}=57^{\circ}",
            ],
        ),
        (
            "right-triangle-acute-angle-ratio",
            "<p>Один острый угол прямоугольного треугольника в 29 раз "
            "больше другого. Найдите больший острый угол.</p>",
            "87",
            [
                r"1x+29x=90^{\circ}\iff30x=90^{\circ}\iff x=3^{\circ}",
                r"29x=29\cdot3^{\circ}=87^{\circ}",
            ],
        ),
    ],
)
def test_elementary_content_rules_build_exact_parent_style_solutions(
    content_rule_key: str,
    condition_html: str,
    answer: str,
    formulas: list[str],
) -> None:
    """Catch a wrong formula family or non-deterministic condition parser."""

    plan = _build_content_plan(
        _elementary_context(condition_html, answer=answer),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key=content_rule_key,
    )

    assert plan.answer == answer
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
    ]
    assert _solution_formulas(plan) == formulas
    solution = plan.transformations[1]["value"]["html"]
    assert "</span>.</p>" not in solution


def test_area_leg_difference_intro_names_both_legs_with_inline_latex() -> None:
    """Keep the variable assignment explicit before the quadratic chain."""

    condition = (
        "<p>Площадь прямоугольного треугольника равна 104. Один из его "
        "катетов на 3 больше другого. Найдите меньший катет.</p>"
    )

    plan = _build_content_plan(
        _elementary_context(condition, answer="13"),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key="right-triangle-area-leg-difference",
    )

    solution = plan.transformations[1]["value"]["html"]
    assert (
        '<p>Пусть <span data-inline-latex="x"></span> — меньший катет, '
        'тогда второй <span data-inline-latex="x+3"></span>:</p>'
        in solution
    )


def test_median_angle_solution_explains_the_isosceles_triangle() -> None:
    """Explain why every segment and base angle equality holds."""

    condition = (
        "<p>В треугольнике ABC угол ACB равен 90°, угол B равен 58°, "
        "CD — медиана. Найдите угол ACD.</p>"
    )

    plan = _build_content_plan(
        _elementary_context(condition, answer="32"),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key="right-triangle-median-angle",
    )

    solution = plan.transformations[1]["value"]["html"]
    assert "точка <span data-inline-latex=\"D\"></span> — середина" in solution
    assert '<span data-inline-latex="AD=BD"></span>' in solution
    assert "равна половине гипотенузы" in solution
    side_equality = '<span data-inline-latex="CD=AD=BD"></span>'
    explanation = (
        '<p>Значит, <span data-inline-latex="\\triangle ACD"></span> '
        "равнобедренный, поэтому его углы при основании равны:</p>"
    )
    angle_equality = '<span data-inline-latex="\\angle ACD='
    assert solution.index(side_equality) < solution.index(explanation)
    assert solution.index(explanation) < solution.index(angle_equality)


def test_bisector_intersection_solution_explains_alpha_construction() -> None:
    """Derive the requested acute angle through the triangle at the intersection."""

    condition = (
        "<p>Острый угол прямоугольного треугольника равен 32°. Найдите "
        "острый угол, образованный биссектрисами этого и прямого углов.</p>"
    )

    plan = _build_content_plan(
        _elementary_context(condition, answer="61"),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key="right-triangle-bisector-intersection-angle",
    )

    solution = plan.transformations[1]["value"]["html"]
    assert (
        '<p>Пусть данный острый угол равен '
        '<span data-inline-latex="\\alpha"></span>. Тогда второй острый угол '
        'равен <span data-inline-latex="90^{\\circ}-\\alpha"></span>.</p>'
        in solution
    )
    assert '<span data-inline-latex="\\angle OAC=\\frac{\\alpha}{2}"></span>' in solution
    assert '<span data-inline-latex="\\angle ACO=45^{\\circ}"></span>' in solution
    assert "по сумме углов треугольника" in solution
    assert '<span data-inline-latex="\\angle AOC=135^{\\circ}-\\frac{\\alpha}{2}"></span>' in solution
    assert "смежный с ним острый угол" in solution


@pytest.mark.parametrize(
    ("content_rule_key", "condition_html", "answer", "required_fragments"),
    [
        (
            "right-triangle-altitude-bisector-angle",
            "<p>Острый угол B прямоугольного треугольника ABC равен 61°. "
            "Найдите угол между высотой CH и биссектрисой CD.</p>",
            "16",
            [
                r'Пусть <span data-inline-latex="\angle B=\alpha"></span>',
                r'<span data-inline-latex="\angle BCH=90^{\circ}-\alpha"></span>',
                r'<span data-inline-latex="\angle ACD=45^{\circ}"></span>',
                r'<span data-inline-latex="\varphi=|\angle BCH-\angle ACD|"></span>',
            ],
        ),
        (
            "right-triangle-altitude-bisector-inverse",
            "<p>В прямоугольном треугольнике угол между высотой и биссектрисой, "
            "проведёнными из вершины прямого угла, равен 21°. Найдите меньший угол.</p>",
            "24",
            [
                r'Пусть <span data-inline-latex="\varphi"></span>',
                r'<span data-inline-latex="\angle ACD=45^{\circ}"></span>',
                r'<span data-inline-latex="\angle ACH=45^{\circ}+\varphi"></span>',
                r'<span data-inline-latex="\angle A=90^{\circ}-\angle ACH"></span>',
            ],
        ),
        (
            "right-triangle-altitude-line-angle",
            "<p>Острый угол B прямоугольного треугольника равен 66°. Найдите "
            "угол между высотой CH и медианой CM.</p>",
            "42",
            [
                r'<span data-inline-latex="CM=BM"></span>',
                r'<span data-inline-latex="\angle BCM=\angle CBM=\angle B"></span>',
                r'<span data-inline-latex="\angle BCH=\angle A"></span>',
                "равнобедренный",
            ],
        ),
        (
            "right-triangle-altitude-median-inverse",
            "<p>В прямоугольном треугольнике угол между высотой и медианой равен "
            "40°. Найдите больший из острых углов.</p>",
            "65",
            [
                r'<span data-inline-latex="CM=MB"></span>',
                r'<span data-inline-latex="\angle CMB=90^{\circ}-\varphi"></span>',
                "равнобедренный",
                r'<span data-inline-latex="\angle CBM=\angle BCM=\frac{180^{\circ}-\angle CMB}{2}"></span>',
            ],
        ),
        (
            "right-triangle-bisector-median-angle",
            "<p>Острый угол B прямоугольного треугольника равен 66°. Найдите "
            "угол между биссектрисой CD и медианой CM.</p>",
            "21",
            [
                r'<span data-inline-latex="CM=BM"></span>',
                r'<span data-inline-latex="\angle BCM=\angle B"></span>',
                r'<span data-inline-latex="\angle ACD=45^{\circ}"></span>',
            ],
        ),
        (
            "right-triangle-bisector-median-inverse",
            "<p>Угол между биссектрисой и медианой прямоугольного треугольника "
            "равен 14°. Найдите меньший угол этого треугольника.</p>",
            "31",
            [
                r'<span data-inline-latex="AM=CM"></span>',
                r'<span data-inline-latex="\angle ACM=\angle A"></span>',
                r'<span data-inline-latex="\angle ACD=45^{\circ}"></span>',
                r'<span data-inline-latex="\varphi=45^{\circ}-\angle A"></span>',
            ],
        ),
        (
            "right-triangle-altitude-length",
            '<p>В треугольнике ABC угол C равен 90°, угол A равен 30°, '
            '<span data-inline-latex="AB=2\\sqrt{3}"></span>. Найдите высоту CH.</p>',
            "1,5",
            [
                r'<span data-inline-latex="AC=AB\cos A"></span>',
                r'<span data-inline-latex="CH=AC\sin A"></span>',
                r'<span data-inline-latex="\cos A=\frac{AC}{AB}"></span>',
                r'<span data-inline-latex="\sin A=\frac{CH}{AC}"></span>',
            ],
        ),
        (
            "right-triangle-hypotenuse-projection-ah",
            "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен "
            "30°, AB = 2. Найдите AH.</p>",
            "1,5",
            [
                r'<span data-inline-latex="AC=AB\cos A"></span>',
                r'<span data-inline-latex="AH=AC\cos A"></span>',
                r'<span data-inline-latex="\cos A=\frac{AH}{AC}"></span>',
            ],
        ),
        (
            "right-triangle-hypotenuse-projection-bh",
            "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен "
            "30°, AB = 4. Найдите BH.</p>",
            "1",
            [
                r'<span data-inline-latex="BC=AB\sin A"></span>',
                r'<span data-inline-latex="BH=BC\sin A"></span>',
                r'<span data-inline-latex="\angle BCH=\angle A"></span>',
                r'<span data-inline-latex="\sin A=\frac{BH}{BC}"></span>',
            ],
        ),
    ],
)
def test_registered_geometry_rules_explain_the_parent_reasoning(
    content_rule_key: str,
    condition_html: str,
    answer: str,
    required_fragments: list[str],
) -> None:
    """Keep each deterministic derivation at least as explicit as its parent."""

    plan = _build_content_plan(
        _elementary_context(condition_html, answer=answer),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key=content_rule_key,
    )

    solution = plan.transformations[1]["value"]["html"]
    for fragment in required_fragments:
        assert fragment in solution


@pytest.mark.parametrize(
    ("content_rule_key", "condition_html", "answer", "formulas"),
    [
        (
            "right-triangle-median-angle",
            "<p>В треугольнике ABC угол ACB равен 90°, угол B равен 58°, "
            "CD — медиана. Найдите угол ACD.</p>",
            "32",
            [
                "CD=AD=BD",
                r"\angle ACD=\angle A=90^{\circ}-\angle B=90^{\circ}-58^{\circ}=32^{\circ}",
            ],
        ),
        (
            "right-triangle-bisector-intersection-angle",
            "<p>Острый угол прямоугольного треугольника равен 32°. Найдите "
            "острый угол, образованный биссектрисами этого и прямого углов.</p>",
            "61",
            [r"\varphi=45^{\circ}+\frac{32^{\circ}}{2}=61^{\circ}"],
        ),
        (
            "right-triangle-altitude-bisector-angle",
            "<p>Острый угол B прямоугольного треугольника ABC равен 61°. "
            "Найдите угол между высотой CH и биссектрисой CD.</p>",
            "16",
            [r"\varphi=\left|61^{\circ}-45^{\circ}\right|=16^{\circ}"],
        ),
        (
            "right-triangle-altitude-bisector-inverse",
            "<p>В прямоугольном треугольнике угол между высотой и биссектрисой, "
            "проведёнными из вершины прямого угла, равен 21°. Найдите меньший угол.</p>",
            "24",
            [r"\alpha_{\min}=45^{\circ}-21^{\circ}=24^{\circ}"],
        ),
        (
            "right-triangle-altitude-line-angle",
            "<p>Острый угол B прямоугольного треугольника равен 66°. Найдите "
            "угол между высотой CH и медианой CM.</p>",
            "42",
            [r"\varphi=\left|66^{\circ}-24^{\circ}\right|=42^{\circ}"],
        ),
        (
            "right-triangle-altitude-line-angle",
            "<p>Острые углы прямоугольного треугольника равны 85° и 5°. "
            "Найдите угол между высотой и биссектрисой.</p>",
            "40",
            [r"\varphi=\left|85^{\circ}-45^{\circ}\right|=40^{\circ}"],
        ),
        (
            "right-triangle-altitude-median-inverse",
            "<p>В прямоугольном треугольнике угол между высотой и медианой равен "
            "40°. Найдите больший из острых углов.</p>",
            "65",
            [r"\alpha_{\max}=\frac{90^{\circ}+40^{\circ}}{2}=65^{\circ}"],
        ),
        (
            "right-triangle-bisector-median-angle",
            "<p>Острый угол B прямоугольного треугольника равен 66°. Найдите "
            "угол между биссектрисой CD и медианой CM.</p>",
            "21",
            [r"\varphi=\left|66^{\circ}-45^{\circ}\right|=21^{\circ}"],
        ),
        (
            "right-triangle-bisector-median-inverse",
            "<p>Угол между биссектрисой и медианой прямоугольного треугольника "
            "равен 14°. Найдите меньший угол этого треугольника.</p>",
            "31",
            [r"\alpha_{\min}=45^{\circ}-14^{\circ}=31^{\circ}"],
        ),
        (
            "right-triangle-altitude-length",
            '<p>В треугольнике ABC угол C равен 90°, угол A равен 30°, '
            '<span data-inline-latex="AB=2\\sqrt{3}"></span>. Найдите высоту CH.</p>',
            "1,5",
            [
                r"CH=AB\sin A\cos A=2\sqrt{3}\cdot\frac{1}{2}\cdot\frac{\sqrt{3}}{2}=\frac{3}{2}"
            ],
        ),
        (
            "right-triangle-hypotenuse-projection-ah",
            "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен "
            "30°, AB = 2. Найдите AH.</p>",
            "1,5",
            [r"AH=AB\cos^{2}A=2\cdot\left(\frac{\sqrt{3}}{2}\right)^{2}=\frac{3}{2}"],
        ),
        (
            "right-triangle-hypotenuse-projection-bh",
            "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен "
            "30°, AB = 4. Найдите BH.</p>",
            "1",
            [r"BH=AB\sin^{2}A=4\cdot\left(\frac{1}{2}\right)^{2}=1"],
        ),
    ],
)
def test_angle_and_altitude_content_rules_build_exact_solutions(
    content_rule_key: str,
    condition_html: str,
    answer: str,
    formulas: list[str],
) -> None:
    """Catch a wrong geometric identity or wrong requested quantity."""

    plan = _build_content_plan(
        _elementary_context(condition_html, answer="ошибка"),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key=content_rule_key,
    )

    assert plan.answer == answer
    assert _solution_formulas(plan) == formulas
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
        "section:answer:1",
    ]


def test_angle_runner_rejects_an_unrelated_requested_angle() -> None:
    """Block a task instead of applying the nearest-looking angle formula."""

    condition = (
        "<p>Острый угол B прямоугольного треугольника равен 61°. "
        "Найдите угол между высотой и медианой.</p>"
    )

    with pytest.raises(RightTrianglePlanError, match="altitude and bisector"):
        _build_content_plan(
            _elementary_context(condition, answer="16"),
            parent_asset_id=PARENT_ASSET_ID,
            content_rule_key="right-triangle-altitude-bisector-angle",
        )


def test_new_elementary_runner_preserves_equivalent_decimal_answer() -> None:
    """Do not rewrite a numerically correct answer that has trailing zeroes."""

    context = _elementary_context(
        '<p>В треугольнике ABC угол C равен 90°, угол A равен 30°, '
        '<span data-inline-latex="AB=2\\sqrt{3}"></span>. Найдите высоту CH.</p>',
        answer="1,50",
    )
    context["normalized_content"]["assets"] = [
        {
            "asset_key": "image_1",
            "asset_id": PARENT_ASSET_ID,
            "url": f"/assets/{PARENT_ASSET_ID}",
            "kind": "ordinary_image",
            "alt": "",
        }
    ]
    context["normalized_content"]["sections"].append(
        {
            "key": "solution",
            "section_id": "solution:1",
            "html": "<p>Существующее содержательное решение.</p>",
        }
    )

    plan = _build_content_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key="right-triangle-altitude-length",
    )

    assert plan.answer == "1,5"
    assert plan.transformations == ()


@pytest.mark.parametrize(
    ("content_rule_key", "condition_html", "answer", "formulas"),
    [
        (
            "right-triangle-median-angle",
            '<p>В треугольнике ABC угол ACB равен '
            '<span data-inline-latex="90"></span>°, угол B равен '
            '<span data-inline-latex="58"></span>°, CD — медиана. '
            "Найдите угол ACD.</p>",
            "32",
            [
                "CD=AD=BD",
                r"\angle ACD=\angle A=90^{\circ}-\angle B=90^{\circ}-58^{\circ}=32^{\circ}",
            ],
        ),
        (
            "right-triangle-altitude-bisector-angle",
            '<p>Один из углов прямоугольного треугольника равен '
            '<span data-inline-latex="86"></span>°. Найдите угол между '
            "высотой и биссектрисой.</p>",
            "41",
            [r"\varphi=\left|86^{\circ}-45^{\circ}\right|=41^{\circ}"],
        ),
        (
            "right-triangle-altitude-bisector-inverse",
            '<p>Угол между высотой и биссектрисой равен '
            '<span data-inline-latex="0^{\\circ}"></span>. '
            "Найдите меньший угол прямоугольного треугольника.</p>",
            "45",
            [r"\alpha_{\min}=45^{\circ}-0^{\circ}=45^{\circ}"],
        ),
        (
            "right-triangle-altitude-length",
            '<p>В треугольнике <span data-inline-latex="ABC"></span> угол C равен '
            '<span data-inline-latex="90^{\\circ}"></span>, угол A равен '
            '<span data-inline-latex="60^\\circ,\\quad AB=2\\sqrt{3}"></span> '
            'Найдите высоту <span data-inline-latex="CH"></span>.</p>',
            "1,5",
            [
                r"CH=AB\sin A\cos A=2\sqrt{3}\cdot\frac{\sqrt{3}}{2}\cdot\frac{1}{2}=\frac{3}{2}"
            ],
        ),
        (
            "right-triangle-hypotenuse-projection-bh",
            '<p>В треугольнике ABC угол C равен '
            '<span data-inline-latex="90^{\\circ}"></span>, '
            '<span data-inline-latex="CH"></span> — высота, угол A равен '
            '<span data-inline-latex="60^\\circ,\\ AB="></span>12. '
            'Найдите <span data-inline-latex="BH"></span>.</p>',
            "9",
            [
                r"BH=AB\sin^{2}A=12\cdot\left(\frac{\sqrt{3}}{2}\right)^{2}=9"
            ],
        ),
    ],
)
def test_new_rules_read_source_split_formula_layouts(
    content_rule_key: str,
    condition_html: str,
    answer: str,
    formulas: list[str],
) -> None:
    """Preserve formula/text order when source spans split values from labels."""

    plan = _build_content_plan(
        _elementary_context(condition_html, answer="ошибка"),
        parent_asset_id=PARENT_ASSET_ID,
        content_rule_key=content_rule_key,
    )

    assert plan.answer == answer
    assert _solution_formulas(plan) == formulas


def test_altitude_plan_adds_asset_and_solution_without_rewriting_correct_answer() -> None:
    """Keep a correct source answer untouched while filling missing content."""

    plan = build_altitude_repair_plan(
        _altitude_context(answer="12,5"),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "12,5"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
    ]
    assert all(item["transformation_target_id"] != "section:answer:1" for item in plan.transformations)
    assert _solution_formulas(plan)[-1].endswith("=\\frac{25}{2}")
    solution_html = next(
        item["value"]["html"]
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    assert (
        'По определению тангенса в <span data-inline-latex="\\triangle ABC"></span>:'
        in solution_html
    )
    assert (
        'По теореме Пифагора для <span data-inline-latex="\\triangle ABC"></span>:'
        in solution_html
    )
    assert (
        'По определению тангенса в <span data-inline-latex="\\triangle ACH"></span>:'
        in solution_html
    )
    assert (
        'По теореме Пифагора для <span data-inline-latex="\\triangle ACH"></span>:'
        in solution_html
    )
    assert "Используем соотношения" not in solution_html


@pytest.mark.parametrize("stored_answer", ["13", "0", "."])
def test_altitude_plan_rewrites_invalid_materialized_answer(stored_answer: str) -> None:
    """Repair a wrong or malformed answer after deriving an exact value."""

    plan = build_altitude_repair_plan(
        _altitude_context(answer=stored_answer),
        parent_asset_id=PARENT_ASSET_ID,
    )

    answer = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:answer:1"
    )
    assert answer["operation"] == "rewrite"
    assert answer["value"]["html"] == '<p><span data-effect="spaced">12,5</span></p>'


def test_altitude_plan_adds_missing_materialized_answer() -> None:
    """Create the canonical answer when the materialized section is absent."""

    context = _altitude_context(answer="12,5")
    context["normalized_content"]["sections"] = [
        section
        for section in context["normalized_content"]["sections"]
        if section["key"] != "answer"
    ]

    plan = build_altitude_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    answer = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:answer:1"
    )
    assert answer["operation"] == "rewrite"
    assert answer["value"]["html"] == '<p><span data-effect="spaced">12,5</span></p>'


def test_altitude_plan_names_the_corresponding_angle_in_bch() -> None:
    """Explain BCH ratios through angle BCH, which corresponds to angle A."""

    context = _altitude_context(answer="20")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, CH — высота, '
        '<span data-inline-latex="BC=25"></span>, '
        '<span data-inline-latex="\\sin A=\\frac{3}{5}"></span>. '
        'Найдите высоту CH.</p>'
    )

    plan = build_altitude_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    solution_html = next(
        item["value"]["html"]
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    assert (
        'Так как <span data-inline-latex="\\angle BCH=\\angle A"></span>, '
        'по определению синуса в '
        '<span data-inline-latex="\\triangle BCH"></span>:'
        in solution_html
    )
    assert (
        'По определению косинуса в '
        '<span data-inline-latex="\\triangle BCH"></span>:'
        not in solution_html
    )


def test_altitude_plan_preserves_existing_human_solution() -> None:
    """Do not replace a substantive solution whose exact answer is verified."""

    plan = build_altitude_repair_plan(
        _altitude_context(
            answer="12,50",
            solution_html="<p>Существующее содержательное решение.</p>",
            asset_id=PARENT_ASSET_ID,
        ),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.transformations == ()


def test_altitude_plan_is_idempotent_after_its_own_solution_materializes() -> None:
    """Accept the current runner marker during post-write readback."""

    initial = build_altitude_repair_plan(
        _altitude_context(answer="12,5"),
        parent_asset_id=PARENT_ASSET_ID,
    )
    solution_html = next(
        item["value"]["html"]
        for item in initial.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    materialized = _altitude_context(
        answer="12,5",
        solution_html=solution_html,
        asset_id=PARENT_ASSET_ID,
    )

    verified = build_altitude_repair_plan(
        materialized,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert verified.transformations == ()


def test_altitude_plan_refreshes_the_previous_solver_version() -> None:
    """Rewrite an older generated proof after the path-selection algorithm changes."""

    initial = build_altitude_repair_plan(
        _altitude_context(answer="12,5"),
        parent_asset_id=PARENT_ASSET_ID,
    )
    current_html = next(
        item["value"]["html"]
        for item in initial.transformations
        if item["transformation_target_id"] == "section:solution"
    )
    assert 'data-content-version="10"' in current_html
    stale_html = current_html.replace(
        'data-content-version="10"',
        'data-content-version="9"',
    )

    refreshed = build_altitude_repair_plan(
        _altitude_context(
            answer="12,5",
            solution_html=stale_html,
            asset_id=PARENT_ASSET_ID,
        ),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert [
        item["transformation_target_id"] for item in refreshed.transformations
    ] == ["section:solution"]
    assert refreshed.transformations[0]["operation"] == "rewrite"


def test_altitude_plan_accepts_current_formula_only_solution() -> None:
    """Treat inline LaTeX as substantive content even without visible prose."""

    solution_html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-altitude-universal" '
        'data-content-version="10" data-solution-title="Решение">'
        '<center><p><span data-inline-latex="CH=20"></span></p></center>'
        '<center><p><span data-inline-latex="\\cos B=\\frac{4}{5}"></span></p></center>'
        '</section>'
    )

    plan = build_altitude_repair_plan(
        _altitude_context(
            answer="12,5",
            solution_html=solution_html,
            asset_id=PARENT_ASSET_ID,
        ),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert all(
        item["transformation_target_id"] != "section:solution"
        for item in plan.transformations
    )


def test_altitude_plan_rejects_unknown_condition_shape() -> None:
    """Propagate the solver's fail-closed behavior through the planner."""

    context = _altitude_context(answer="1")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, CH — высота, '
        '<span data-inline-latex="AB=13"></span>. Найдите AH.</p>'
    )

    with pytest.raises(RightTrianglePlanError, match="cannot derive AH"):
        build_altitude_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)


def test_plan_adds_parent_image_solution_and_only_corrects_wrong_answer() -> None:
    """Catch an omitted repair when an eligible task lacks both asset and solution."""

    plan = build_repair_plan(_context(answer="7"), parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "5"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
        "section:answer:1",
    ]
    assert _solution_formulas(plan) == [
        r"\cos A=\sqrt{1-\sin^2 A}=\sqrt{1-\left(\frac{3}{5}\right)^2}=\frac{4}{5}",
        r"AB=\frac{AC}{\cos A}=\frac{4}{\frac{4}{5}}=5",
    ]
    solution = plan.transformations[1]["value"]["html"]
    assert "Найдём косинус угла" in solution
    assert "Следовательно," in solution


@pytest.mark.parametrize(
    ("condition_html", "answer", "formulas"),
    [
        (
            '<p>В треугольнике ABC угол C равен 90°, '
            '<span data-inline-latex="\\sin A=0{,}5"></span>, '
            '<span data-inline-latex="BC=4"></span>. Найдите AB.</p>',
            "8",
            [
                r"\sin A=\frac{BC}{AB}\iff AB=\frac{BC}{\sin A}=\frac{4}{0{,}5}=8",
            ],
        ),
        (
            '<p>В треугольнике ABC угол A равен 90°, '
            '<span data-inline-latex="\\cos B=\\frac{3}{5}"></span>, '
            '<span data-inline-latex="AB=12"></span>. Найдите BC.</p>',
            "20",
            [
                r"\cos B=\frac{AB}{BC}\iff BC=\frac{AB}{\cos B}=\frac{12}{\frac{3}{5}}=20",
            ],
        ),
        (
            '<p>В треугольнике ABC угол B равен 90°, '
            '<span data-inline-latex="\\tg C=\\frac{3}{4}"></span>, '
            '<span data-inline-latex="BC=4"></span>. Найдите AB.</p>',
            "3",
            [
                r"\tg C=\frac{AB}{BC}\iff AB=BC\cdot\tg C=4\cdot \frac{3}{4}=3",
            ],
        ),
        (
            '<p>В треугольнике ABC угол A равен 90°, '
            '<span data-inline-latex="\\ctg C=\\frac{4}{3}"></span>, '
            '<span data-inline-latex="AB=6"></span>. Найдите AC.</p>',
            "8",
            [
                r"\ctg C=\frac{AC}{AB}\iff AC=AB\cdot\ctg C=6\cdot \frac{4}{3}=8",
            ],
        ),
    ],
)
def test_universal_plan_normalizes_all_functions_and_right_angle_positions(
    condition_html: str,
    answer: str,
    formulas: list[str],
) -> None:
    """Catch hard-coded C/right-angle or sin-only side interpretation."""

    context = _context(answer="999")
    context["normalized_content"]["sections"][0]["html"] = condition_html

    plan = build_universal_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == answer
    assert _solution_formulas(plan) == formulas


def test_universal_plan_reads_degree_value_from_a_separate_inline_formula() -> None:
    """Recognize source HTML that splits the angle label and 90-degree value."""

    context = _context(answer="20")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен '
        '<span data-inline-latex="90^{\\circ}"></span>, '
        '<span data-inline-latex="BC=16"></span>, '
        '<span data-inline-latex="\\sin A=0{,}8"></span>. Найдите AB.</p>'
    )

    plan = build_universal_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "20"
    assert _solution_formulas(plan) == [
        r"\sin A=\frac{BC}{AB}\iff AB=\frac{BC}{\sin A}=\frac{16}{0{,}8}=20"
    ]


def test_universal_plan_uses_three_rows_when_known_side_is_outside_tangent_ratio() -> None:
    """Derive a requested leg from the hypotenuse without inventing a prototype."""

    context = _context(answer="6")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\tg A=\\frac{3}{4}"></span>, '
        '<span data-inline-latex="AB=10"></span>. Найдите BC.</p>'
    )

    plan = build_universal_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "6"
    assert _solution_formulas(plan) == [
        r"\tg A=\frac{BC}{AC}",
        r"AC=\frac{AB}{\sqrt{1+(\tg A)^2}}=\frac{10}{\sqrt{1+(\frac{3}{4})^2}}=8",
        r"BC=AC\cdot\tg A=8\cdot \frac{3}{4}=6",
    ]


def test_universal_plan_names_complementary_sine_before_using_it() -> None:
    """Make the cosine-to-sine transition explicit in the displayed algebra."""

    context = _context(answer="8")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="BC=5"></span>, '
        '<span data-inline-latex="\\cos A=\\frac{8\\sqrt{89}}{89}"></span>. '
        'Найдите AC.</p>'
    )

    plan = build_universal_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert _solution_formulas(plan) == [
        r"\sin A=\sqrt{1-\cos A^2}=\sqrt{1-(\frac{8\sqrt{89}}{89})^2}=\frac{5\sqrt{89}}{89}",
        r"\sin A=\frac{BC}{AB}\iff AB=\frac{BC}{\sin A}=\frac{5}{\frac{5\sqrt{89}}{89}}=\sqrt{89}",
        r"\cos A=\frac{AC}{AB}\iff AC=AB\cdot\cos A=\sqrt{89}\cdot \frac{8\sqrt{89}}{89}=8",
    ]


def test_universal_plan_preserves_existing_solution_when_computed_answer_matches() -> None:
    """Allow the shared Helpers stage after validating untouched content."""

    context = _context(
        answer="8,0",
        solution_html="<p>Существующее содержательное решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=0{,}5"></span>, '
        '<span data-inline-latex="BC=4"></span>. Найдите AB.</p>'
    )

    plan = build_universal_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "8"
    assert plan.transformations == ()


def test_universal_plan_rewrites_its_legacy_direct_solution_with_iff() -> None:
    """Upgrade only runner-owned direct algebra without touching human solutions."""

    legacy_solution = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-universal" '
        'data-solution-title="Решение">'
        '<center><p><span data-inline-latex="\\sin A=\\frac{BC}{AB}"></span>.</p></center>'
        '<center><p><span data-inline-latex="AB=\\frac{BC}{\\sin A}='
        '\\frac{4}{0{,}5}=8"></span>.</p></center></section>'
    )
    context = _context(
        answer="8",
        solution_html=legacy_solution,
        asset_id=PARENT_ASSET_ID,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=0{,}5"></span>, '
        '<span data-inline-latex="BC=4"></span>. Найдите AB.</p>'
    )

    plan = build_universal_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:solution"
    ]
    assert _solution_formulas(plan) == [
        r"\sin A=\frac{BC}{AB}\iff AB=\frac{BC}{\sin A}=\frac{4}{0{,}5}=8",
    ]
    solution_html = plan.transformations[0]["value"]["html"]
    assert "</span>.</p>" not in solution_html


def test_universal_plan_finds_requested_sine_from_two_known_legs() -> None:
    """Support the inverse variant where the condition asks for a trig value."""

    context = _context(answer="0,7")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="AC=\\sqrt{51}"></span>, '
        '<span data-inline-latex="BC=7"></span>. Найдите '
        '<span data-inline-latex="\\sin A"></span>.</p>'
    )

    plan = build_universal_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "0,7"
    assert _solution_formulas(plan) == [
        r"AB=\sqrt{AC^{2}+BC^{2}}=\sqrt{(\sqrt{51})^{2}+(7)^{2}}=10",
        r"\sin A=\frac{BC}{AB}=\frac{7}{10}=0{,}7",
    ]
    assert all(
        item["transformation_target_id"] != "section:answer:1"
        for item in plan.transformations
    )


@pytest.mark.parametrize(
    ("condition_html", "answer", "formulas"),
    [
        (
            '<p>В треугольнике ABC угол A равен 90°, '
            '<span data-inline-latex="AB=3"></span>, '
            '<span data-inline-latex="BC=5"></span>. Найдите '
            '<span data-inline-latex="\\cos B"></span>.</p>',
            "0,6",
            [r"\cos B=\frac{AB}{BC}=\frac{3}{5}=0{,}6"],
        ),
        (
            '<p>В треугольнике ABC угол B равен 90°, '
            '<span data-inline-latex="AB=6"></span>, '
            '<span data-inline-latex="BC=8"></span>. Найдите '
            '<span data-inline-latex="\\tg C"></span>.</p>',
            "0,75",
            [r"\tg C=\frac{AB}{BC}=\frac{6}{8}=0{,}75"],
        ),
        (
            '<p>В треугольнике ABC угол C равен 90°, '
            '<span data-inline-latex="AC=4"></span>, '
            '<span data-inline-latex="BC=8"></span>. Найдите '
            '<span data-inline-latex="\\ctg A"></span>.</p>',
            "0,5",
            [r"\ctg A=\frac{AC}{BC}=\frac{4}{8}=0{,}5"],
        ),
    ],
)
def test_universal_plan_finds_requested_cos_tg_and_ctg(
    condition_html: str,
    answer: str,
    formulas: list[str],
) -> None:
    """Keep all requested trig functions on the same side-role engine."""

    context = _context(answer=answer)
    context["normalized_content"]["sections"][0]["html"] = condition_html

    plan = build_universal_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == answer
    assert _solution_formulas(plan) == formulas


def test_universal_plan_rejects_trigonometry_of_the_right_angle() -> None:
    """Prevent sin 90 degrees from pretending to determine another side."""

    context = _context(answer="8", asset_id=PARENT_ASSET_ID)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол B равен 90°, '
        '<span data-inline-latex="\\sin B=1"></span>, '
        '<span data-inline-latex="BC=4"></span>. Найдите AB.</p>'
    )

    with pytest.raises(RightTrianglePlanError, match="must be acute"):
        build_universal_repair_plan(
            context,
            parent_asset_id=PARENT_ASSET_ID,
        )


def test_plan_recognizes_latex_requested_side_and_reduces_decimal_sine() -> None:
    """Preserve the requested side while turning a decimal sine into a fraction."""

    context = _context(answer="75")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=0{,}8"></span>, '
        '<span data-inline-latex="AC=15"></span>. Найдите '
        '<span data-inline-latex="AB"></span>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "25"
    assert _solution_formulas(plan) == [
        r"\sin A=0{,}8=\frac{8}{10}=\frac{4}{5}",
        r"\cos A=\sqrt{1-\sin^2 A}=\sqrt{1-\left(\frac{4}{5}\right)^2}=\frac{3}{5}",
        r"AB=\frac{AC}{\cos A}=\frac{15}{\frac{3}{5}}=25",
    ]


def test_plan_reduces_decimal_cosine_before_four_standard_rows() -> None:
    """Use a decimal cosine directly after rendering its reduced fraction."""

    context = _context(answer="75")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\cos A=0{,}8"></span>, '
        '<span data-inline-latex="AC=15"></span>. Найдите '
        '<span data-inline-latex="AB"></span>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "18,75"
    assert _solution_formulas(plan) == [
        r"\cos A=0{,}8=\frac{8}{10}=\frac{4}{5}",
        r"AB=\frac{AC}{\cos A}=\frac{15}{\frac{4}{5}}=18{,}75",
    ]


def test_cosine_hypotenuse_rule_accepts_cyrillic_sides_only_for_ab() -> None:
    """Require cos A and requested AB while accepting source Cyrillic side labels."""

    context = _context(
        answer="8",
        solution_html="<p>Корректное решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    condition = context["normalized_content"]["sections"][0]
    condition["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, <i>АС</i> = 4, '
        '<span data-inline-latex="\\cos A=0{,}5"></span>. '
        'Найдите <i>АВ</i>.</p>'
    )

    plan = build_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
        required_trig_name="cos",
        required_requested="AB",
    )

    assert plan.answer == "8"
    assert plan.transformations == ()

    condition["html"] = condition["html"].replace("Найдите <i>АВ</i>", "Найдите AC")
    with pytest.raises(RightTrianglePlanError, match="must request AB"):
        build_repair_plan(
            context,
            parent_asset_id=PARENT_ASSET_ID,
            required_trig_name="cos",
            required_requested="AB",
        )

    condition["html"] = condition["html"].replace("Найдите AC", "Найдите <i>АВ</i>")
    condition["html"] = condition["html"].replace(r"\cos A", r"\sin A")
    with pytest.raises(RightTrianglePlanError, match="must use cos A"):
        build_repair_plan(
            context,
            parent_asset_id=PARENT_ASSET_ID,
            required_trig_name="cos",
            required_requested="AB",
        )


def test_tangent_bc_plan_joins_definition_and_rearrangement_with_iff() -> None:
    """Build the 27243 calculation as one equivalence chain."""

    context = _context(answer="12", asset_id="old-asset")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, <i>АС</i> = 20, '
        '<span data-inline-latex="\\tg A=0{,}75"></span>. '
        'Найдите <var data-math-identifier="BC">BC</var>.</p>'
    )

    plan = build_tangent_bc_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "15"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
        "section:answer:1",
    ]
    assert _solution_formulas(plan) == [
        r"\tg A=\frac{BC}{AC}\iff BC=AC\tg A=20\cdot 0{,}75=15",
    ]
    solution_html = plan.transformations[1]["value"]["html"]
    assert "По опре\u00adде\u00adле\u00adнию тан\u00adген\u00adса:" in solution_html


def test_tangent_bc_plan_rewrites_its_older_two_row_solution() -> None:
    """Migrate only solutions previously generated by this content rule."""

    context = _context(
        answer="15",
        asset_id=PARENT_ASSET_ID,
        solution_html=(
            '<section data-content-kind="solution" '
            'data-content-rule="right-triangle-tangent-opposite-cathetus" '
            'data-solution-title="Решение">'
            '<p>По определению тангенса:</p>'
            '<center><p><span data-inline-latex="\\tg A=\\frac{BC}{AC}"></span>.</p></center>'
            '<center><p><span data-inline-latex="BC=AC\\tg A=20\\cdot 0{,}75=15"></span>.</p></center>'
            '</section>'
        ),
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p><span data-inline-latex="AC=20"></span>, '
        '<span data-inline-latex="\\tg A=0{,}75"></span>. Найдите BC.</p>'
    )

    plan = build_tangent_bc_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:solution"
    ]
    assert plan.transformations[0]["operation"] == "rewrite"
    assert _solution_formulas(plan) == [
        r"\tg A=\frac{BC}{AC}\iff BC=AC\tg A=20\cdot 0{,}75=15",
    ]


@pytest.mark.parametrize(
    ("condition_html", "message"),
    [
        (
            '<p><span data-inline-latex="AC=8"></span>, '
            '<span data-inline-latex="\\tg A=0{,}5"></span>. Найдите AB.</p>',
            "must request BC",
        ),
        (
            '<p><span data-inline-latex="AC=8"></span>, '
            '<span data-inline-latex="\\cos A=0{,}5"></span>. Найдите BC.</p>',
            "must use tg A",
        ),
        (
            '<p><span data-inline-latex="AB=8"></span>, '
            '<span data-inline-latex="\\tg A=0{,}5"></span>. Найдите BC.</p>',
            "must give AC",
        ),
    ],
)
def test_tangent_bc_plan_rejects_every_other_condition_shape(
    condition_html: str,
    message: str,
) -> None:
    """Block transformations unless tg A, AC, and requested BC all match."""

    context = _context(answer="4", asset_id=PARENT_ASSET_ID)
    context["normalized_content"]["sections"][0]["html"] = condition_html

    with pytest.raises(RightTrianglePlanError, match=message):
        build_tangent_bc_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)


def test_tangent_hypotenuse_rule_copies_parent_method_with_definition_first() -> None:
    """Rewrite tangent solutions to the approved definition-and-Pythagoras HTML."""

    context = _context(
        answer="7",
        solution_html="<p>Старое решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\tg A=\\frac{33}{4\\sqrt{33}}"></span>, '
        '<i>АС</i> = 4. Найдите <i>АВ</i>.</p>'
    )

    plan = build_repair_plan(
        context,
        parent_asset_id=PARENT_ASSET_ID,
        required_trig_name="tg",
        required_requested="AB",
    )

    assert plan.answer == "7"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:solution"
    ]
    assert _solution_formulas(plan) == [
        r"\tg A=\frac{BC}{AC}",
        r"BC=AC\cdot\tg A=4\cdot \frac{33}{4\sqrt{33}}=\sqrt{33}",
        r"AB=\sqrt{AC^{2}+BC^{2}}=\sqrt{16+33}=\sqrt{49}=7",
    ]
    solution = plan.transformations[0]["value"]["html"]
    assert 'data-content-rule="right-triangle-tangent-hypotenuse"' in solution
    assert 'data-solution-title="Приведем другое решение:"' in solution


@pytest.mark.parametrize(
    ("trig_latex", "requested", "error"),
    [
        (r"\cos A=\frac{4}{7}", "AB", "must use tg A"),
        (r"\tg A=\frac{3}{4}", "BC", "must request AB"),
    ],
)
def test_tangent_hypotenuse_rule_rejects_wrong_condition_shape(
    trig_latex: str,
    requested: str,
    error: str,
) -> None:
    """Block non-tangent inputs and any requested side other than AB."""

    context = _context(answer="7", asset_id=PARENT_ASSET_ID)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        f'<span data-inline-latex="{trig_latex}"></span>, '
        f'<span data-inline-latex="AC=4"></span>. Найдите {requested}.</p>'
    )

    with pytest.raises(RightTrianglePlanError, match=error):
        build_repair_plan(
            context,
            parent_asset_id=PARENT_ASSET_ID,
            required_trig_name="tg",
            required_requested="AB",
        )


def test_plan_rewrites_only_the_pipeline_verbose_solution_shape() -> None:
    """Replace the mechanical cosine-squared rows without touching other solutions."""

    verbose = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        '<center><p><span data-inline-latex="\\cos^2 A=1-\\sin^2 A">'
        "</span>.</p></center></section>"
    )
    plan = build_repair_plan(
        _context(answer="5", solution_html=verbose, asset_id=PARENT_ASSET_ID),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:solution"
    ]
    replacement = plan.transformations[0]["value"]["html"]
    assert "Найдём косинус угла" in replacement
    assert "Следовательно," in replacement
    assert r"\cos^2 A" not in replacement


def test_plan_simplifies_and_rewrites_pipeline_radical_cosine() -> None:
    """Render sqrt(265/841) as sqrt(265)/29 and replace the old expanded form."""

    context = _context(
        answer="29",
        solution_html=(
            '<section data-content-kind="solution" data-solution-title="Решение">'
            '<p>Найдём косинус угла <var data-math-identifier="A">A</var>:</p>'
            '<center><p><span data-inline-latex="'
            "\\cos A=\\sqrt{1-\\sin^2 A}="
            "\\sqrt{1-\\left(\\frac{24}{29}\\right)^2}="
            "\\frac{\\sqrt{222865}}{841}"
            '"></span>.</p></center><p>Следовательно,</p></section>'
        ),
        asset_id=PARENT_ASSET_ID,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=\\frac{24}{29}"></span>, '
        '<span data-inline-latex="AC=\\sqrt{265}"></span>. Найдите '
        '<var data-math-identifier="AB">AB</var>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:solution"
    ]
    assert _solution_formulas(plan) == [
        r"\cos A=\sqrt{1-\sin^2 A}=\sqrt{1-\left(\frac{24}{29}\right)^2}=\frac{\sqrt{265}}{29}",
        r"AB=\frac{AC}{\cos A}=\frac{\sqrt{265}}{\frac{\sqrt{265}}{29}}=29",
    ]


def test_plan_preserves_existing_solution_and_correct_answer() -> None:
    """Catch destructive rewrites when only a non-prototype image needs repair."""

    plan = build_repair_plan(
        _context(
            answer="5",
            solution_html="<p>Сохранить это решение.</p>",
            asset_id="e95a7071-cff1-477d-85ca-a4b51bbb68b3",
        ),
        parent_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "5"
    assert plan.transformations == (
        {
            "transformation_target_id": "asset:image_1",
            "operation": "add",
            "value": {
                "parent_target_id": "section:condition:1",
                "position": 0,
                "asset_key": "image_1",
                "asset_id": PARENT_ASSET_ID,
                "url": f"/assets/{PARENT_ASSET_ID}",
                "kind": "ordinary_image",
                "alt": "",
            },
        },
    )


def test_plan_verifies_ac_answer_when_hypotenuse_is_given() -> None:
    """Catch treating an AB-to-AC task as unsupported merely because it has a solution."""

    context = _context(
        answer="3,6",
        solution_html="<p>Уже есть решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    condition = context["normalized_content"]["sections"][0]
    condition["html"] = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол C равен 90°, '
        '<span data-inline-latex="AB=4"></span> и '
        '<span data-inline-latex="\\sin A=\\frac{\\sqrt{19}}{10}"></span>. '
        'Найдите <var data-math-identifier="AC">AC</var>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "3,6"
    assert plan.transformations == ()


def test_plan_repairs_ac_to_bc_task_and_removes_solution_image() -> None:
    """Support the 27239 rule while preserving its already-correct answer."""

    context = _context(
        answer="2",
        solution_html=(
            '<p><img data-asset-id="old-asset" data-asset-key="image_1" '
            'src="/assets/old-asset"/>Старое решение.</p>'
        ),
        asset_id="old-asset",
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=\\frac{\\sqrt{5}}{5}"></span>, '
        '<span data-inline-latex="AC=4"></span>. Найдите '
        '<var data-math-identifier="BC">BC</var>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "2"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
    ]
    assert _solution_formulas(plan) == [
        r"\cos A=\sqrt{1-\sin^{2} A}=\sqrt{1-(\frac{\sqrt{5}}{5})^{2}}=\frac{2\sqrt{5}}{5}",
        r"AB=\frac{AC}{\cos A}=\frac{4}{\frac{2\sqrt{5}}{5}}=2\sqrt{5}",
        r"BC=\sqrt{AB^{2}-AC^{2}}=\sqrt{(2\sqrt{5})^{2}-4^{2}}=2",
    ]
    solution_html = plan.transformations[1]["value"]["html"]
    assert 'data-solution-title="Альтернативное решение."' in solution_html
    assert "<p><b>Альтернативное решение.</b></p>" in solution_html
    assert "Най\u00adдем ко\u00adси\u00adнус угла <i>А</i>:" in solution_html
    assert "Най\u00adдем длину ги\u00adпо\u00adте\u00adну\u00adзы" in solution_html
    assert "По те\u00adо\u00adре\u00adме Пи\u00adфа\u00adго\u00adра най\u00adдем длину ка\u00adте\u00adта" in solution_html
    assert "<img" not in solution_html


def test_plan_preserves_complete_ac_to_bc_task_with_scaled_radical_sine() -> None:
    """Accept the exact sine shape used by sampled task 4651."""

    context = _context(
        answer="34",
        solution_html="<p>Имеем корректное решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="\\sin A=\\frac{2\\sqrt{5}}{5}"></span>, '
        '<span data-inline-latex="AC=17"></span>. Найдите '
        '<var data-math-identifier="BC">BC</var>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "34"
    assert plan.transformations == ()


def test_plan_rejects_condition_outside_the_three_explicit_side_rules() -> None:
    """Prevent a requested side alone from silently selecting the wrong formula."""

    context = _context(answer="4", asset_id=PARENT_ASSET_ID)
    condition = context["normalized_content"]["sections"][0]
    condition["html"] = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="AB=4"></span>, '
        '<span data-inline-latex="\\sin A=\\frac{3}{5}"></span>. '
        'Найдите <var data-math-identifier="AB">AB</var>.</p>'
    )

    with pytest.raises(RightTrianglePlanError, match="supported side rules"):
        build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)


def test_plan_accepts_parent_ac_written_outside_latex_span() -> None:
    """Catch rejection of the actual prototype's plain-text decimal side value."""

    context = _context(
        answer="5",
        solution_html="<p>Решение прототипа.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    condition = context["normalized_content"]["sections"][0]
    condition["html"] = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол C равен 90°, '
        '<var data-math-identifier="AC">AC</var> = 4,8, '
        '<span data-inline-latex="\\sin A=\\frac{7}{25}"></span>. '
        'Най\u00adди\u00adте <var data-math-identifier="AB">AB</var>.</p>'
    )

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "5"
    assert plan.transformations == ()


def test_plan_adds_answer_section_when_it_is_completely_absent() -> None:
    """Catch blocking a valid future-group task merely because answer has no section."""

    context = _context(
        answer="5",
        solution_html="<p>Готовое решение.</p>",
        asset_id=PARENT_ASSET_ID,
    )
    content = context["normalized_content"]
    content["sections"] = [
        section for section in content["sections"] if section["key"] != "answer"
    ]

    plan = build_repair_plan(context, parent_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "5"
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "section:answer:1"
    ]


class _DryRunGateway:
    """Expose one group member while rejecting every unintended write."""

    def __init__(self) -> None:
        """Create the one target that the runner should plan."""

        self.context = _context(answer="7")

    def get_source_catalog_children(self, parent_id: str, parent_type: str) -> dict:
        """Return the minimal ordered source-group shape supplied by MCP."""

        assert parent_id == "group-27238"
        assert parent_type == "group"
        return {
            "children": [
                {
                    "id": "problem-1",
                    "source_problem_id": "4583",
                    "node_type": "problem",
                }
            ]
        }

    def get_problem_context(self, problem_id: str) -> dict:
        """Return the materialized context for the discovered problem."""

        assert problem_id == "problem-1"
        return self.context

    def apply_problem_transformations(self, problem_id: str, transformations: list[dict]) -> dict:
        """Fail if a preview ever tries to modify source content."""

        raise AssertionError("dry-run must not write transformations")


def test_manifest_preview_discovers_group_and_never_writes() -> None:
    """Catch a dry-run branch that mutates a source task before reporting its plan."""

    summary = run_manifest(
        _DryRunGateway(),
        {
            "source_group_id": "group-27238",
            "condition_asset": {"source_asset_id": PARENT_ASSET_ID},
            "selection": {"skip_source_problem_ids": [], "require_normalized_schema_version": 3},
        },
        apply=False,
    )

    assert summary["planned_count"] == 1
    assert summary["applied_count"] == 0
    assert summary["results"] == [
        {
            "source_problem_id": "4583",
            "problem_id": "problem-1",
            "status": "planned",
            "transformations": ["asset:image_1", "section:solution", "section:answer:1"],
        }
    ]
