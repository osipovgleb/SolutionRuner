"""Verify deterministic solution repair for isosceles-triangle source groups."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.triangles.isosceles.planner import (
    IsoscelesTrianglePlanError,
    build_group_27285_repair_plan,
    build_group_27286_repair_plan,
    build_group_27287_repair_plan,
    build_group_27288_repair_plan,
    build_group_27289_repair_plan,
    build_group_27320_repair_plan,
    build_group_27321_repair_plan,
    build_group_27322_repair_plan,
    build_group_27323_repair_plan,
    build_group_27324_repair_plan,
    build_group_27325_repair_plan,
    build_group_27326_repair_plan,
    build_group_27327_repair_plan,
    build_group_27328_repair_plan,
    build_group_27329_repair_plan,
    build_group_27330_repair_plan,
    build_group_27331_repair_plan,
    build_group_27345_repair_plan,
    build_group_27346_repair_plan,
    build_group_27347_repair_plan,
    build_group_27349_repair_plan,
    build_group_27350_repair_plan,
    build_group_27351_repair_plan,
    build_group_27352_repair_plan,
    build_group_27353_repair_plan,
    build_group_27589_repair_plan,
    build_group_27590_repair_plan,
    build_group_27619_repair_plan,
    build_group_27620_repair_plan,
    build_group_27621_repair_plan,
    build_group_27744_repair_plan,
    build_group_27745_repair_plan,
    build_group_27746_repair_plan,
    build_group_27747_repair_plan,
    build_group_27748_repair_plan,
    build_group_27750_repair_plan,
    build_group_27754_repair_plan,
    build_group_27760_repair_plan,
    build_group_27792_repair_plan,
    build_group_27793_repair_plan,
    build_group_27794_repair_plan,
    build_group_27795_repair_plan,
    build_group_27796_repair_plan,
    build_group_27797_repair_plan,
    build_group_27798_repair_plan,
    build_group_27799_repair_plan,
    build_group_27800_repair_plan,
    build_group_628232_repair_plan,
    build_group_676342_repair_plan,
    build_group_701874_repair_plan,
    build_repair_plan,
)


PARENT_ASSET_ID = "6c4f65f7-c74b-438a-8599-47ba154243ff"
PARENT_SOLUTION_ASSETS = (
    {
        "asset_key": "image_2",
        "source_asset_id": PARENT_ASSET_ID,
        "url": f"/assets/{PARENT_ASSET_ID}",
        "alt": "",
    },
)


def _context(condition_html: str, answer: str, solution: str = "") -> dict[str, object]:
    """Build the normalized subset consumed by the pure planner."""

    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "html": condition_html,
            "asset_keys": [],
        },
        {
            "key": "answer",
            "section_id": "answer:1",
            "transformation_target_id": "section:answer:1",
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            "asset_keys": [],
        },
    ]
    if solution:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
                "html": solution,
                "asset_keys": [],
            }
        )
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": sections,
            "assets": [],
        }
    }


@pytest.mark.parametrize(
    ("side", "sine", "answer", "expected"),
    [
        ("4", r"\frac{3\sqrt{11}}{10}", "0,8", "0,8"),
        ("25", r"\frac{3\sqrt{11}}{10}", "5", "5"),
        ("25", r"\frac{3}{5}", "40", "40"),
        ("18", r"\frac{\sqrt{15}}{4}", ".", "9"),
    ],
)
def test_group_27284_adapts_parent_method_and_computes_exact_answer(
    side: str,
    sine: str,
    answer: str,
    expected: str,
) -> None:
    """Cover the parent samples and a known malformed source answer."""

    context = _context(
        '<p>В треугольнике <span data-inline-latex="AC=BC='
        + side
        + '"></span>, <span data-inline-latex="\\sin B='
        + sine
        + '"></span>. Найдите <span data-inline-latex="AB"></span>.</p>',
        answer,
    )

    plan = build_repair_plan(context, parent_condition_asset_id=PARENT_ASSET_ID)

    assert plan.answer == expected
    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    assert by_target["asset:image_1"]["value"]["asset_id"] == PARENT_ASSET_ID
    solution = by_target["section:solution"]["value"]["html"]
    assert "равнобедренный" in solution
    assert "AB=2AH=2AC\\cos B" in solution
    assert rf"2\cdot {side}" in solution
    if answer != expected:
        assert by_target["section:answer:1"]["value"]["html"].endswith(
            f">{expected}</span></p>"
        )
    else:
        assert "section:answer:1" not in by_target


def test_existing_solution_is_preserved_while_content_is_verified() -> None:
    """Never rewrite a substantive solution or an already-correct answer."""

    existing = "<p>Существующее корректное решение.</p>"
    context = _context(
        '<p><span data-inline-latex="AC=BC=5"></span>, '
        '<span data-inline-latex="\\sin A=\\frac{4}{5}"></span>. '
        'Найдите <span data-inline-latex="AB"></span></p>',
        "6",
        existing,
    )
    context["normalized_content"]["assets"] = [  # type: ignore[index]
        {"asset_key": "image_1", "asset_id": PARENT_ASSET_ID}
    ]

    plan = build_repair_plan(context, parent_condition_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "6"
    assert plan.transformations == ()


def test_existing_solution_image_is_moved_to_centered_condition_without_changing_proof() -> None:
    """Relocate the parent diagram even when its substantive solution is preserved."""

    context = _context(
        '<p>В равнобедренном треугольнике ABC с основанием AB боковая сторона '
        'равна <span data-inline-latex="16\\sqrt{15}"></span>, '
        '<span data-inline-latex="\\sin \\angle BAC=0{,}25"></span>. '
        'Найдите длину высоты <span data-inline-latex="AH"></span>.</p>',
        "30",
        (
            f'<p><img data-asset-id="{PARENT_ASSET_ID}" data-asset-key="image_1" '
            f'src="/assets/{PARENT_ASSET_ID}"/></p><p>Содержательное доказательство.</p>'
        ),
    )
    content = context["normalized_content"]
    content["assets"] = [
        {
            "asset_key": "image_1",
            "asset_id": PARENT_ASSET_ID,
            "url": f"/assets/{PARENT_ASSET_ID}",
            "kind": "ordinary_image",
            "alt": "",
        }
    ]
    next(
        section for section in content["sections"] if section["key"] == "solution"
    )["asset_keys"] = ["image_1"]

    plan = build_group_27326_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    assert by_target["asset:image_1"]["value"]["parent_target_id"] == "section:condition:1"
    assert by_target["asset:image_1"]["value"]["html"].startswith("<center><img")
    rewritten = by_target["section:solution:1"]["value"]
    assert rewritten["asset_keys"] == []
    assert "image_1" not in rewritten["html"]
    assert "Содержательное доказательство." in rewritten["html"]


def test_unknown_condition_shape_fails_before_transformations() -> None:
    """Reject another requested quantity instead of guessing a method."""

    context = _context(
        '<p><span data-inline-latex="AC=BC=5"></span>, '
        '<span data-inline-latex="\\sin A=\\frac{4}{5}"></span>. '
        'Найдите <span data-inline-latex="AH"></span>.</p>',
        "3",
    )

    with pytest.raises(IsoscelesTrianglePlanError, match="request AB"):
        build_repair_plan(context, parent_condition_asset_id=PARENT_ASSET_ID)


def test_source_soft_hyphens_do_not_hide_the_requested_base() -> None:
    """Normalize the source site's discretionary word breaks before validation."""

    context = _context(
        '<p><span data-inline-latex="AC=BC=4"></span>, '
        '<span data-inline-latex="\\sin B=\\frac{3}{5}"></span>. '
        'Най\u00adди\u00adте <i>АВ</i>.</p>',
        "6,4",
    )

    plan = build_repair_plan(context, parent_condition_asset_id=PARENT_ASSET_ID)

    assert plan.answer == "6,4"


@pytest.mark.parametrize(
    ("base", "sine", "current_answer", "expected"),
    [
        ("6", r"0{,}8", "5", "5"),
        ("14", r"0{,}96", "25", "25"),
        ("24", r"0{,}6", "20", "15"),
        (r"2\sqrt{51}", r"0{,}7", "5", "10"),
    ],
)
def test_group_27285_strictly_derives_equal_side_from_base_and_sine(
    base: str,
    sine: str,
    current_answer: str,
    expected: str,
) -> None:
    """Adapt only the inverse parent method and repair disproved answers."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\sin A={sine}"></span>. '
        'Найдите <span data-inline-latex="AC"></span>.</p>',
        current_answer,
    )

    plan = build_group_27285_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == expected
    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    solution = by_target["section:solution"]["value"]["html"]
    assert r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}" in solution
    if current_answer == expected:
        assert "section:answer:1" not in by_target
    else:
        assert by_target["section:answer:1"]["value"]["html"].endswith(
            f">{expected}</span></p>"
        )


def test_group_27285_rejects_another_requested_side() -> None:
    """Keep the group contract narrower than a universal triangle solver."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=6"></span>, '
        '<span data-inline-latex="\\sin A=0{,}8"></span>. '
        'Найдите <span data-inline-latex="BC"></span>.</p>',
        "5",
    )

    with pytest.raises(IsoscelesTrianglePlanError, match="request AC"):
        build_group_27285_repair_plan(
            context,
            parent_condition_asset_id=PARENT_ASSET_ID,
        )


def test_group_27286_uses_direct_cosine_to_find_the_base() -> None:
    """Keep the direct-cosine base rule distinct from the preceding sine rule."""

    context = _context(
        '<p><span data-inline-latex="AC=BC=14"></span>, '
        '<span data-inline-latex="\\cos A=0{,}5"></span>. '
        'Найдите <span data-inline-latex="AB"></span>.</p>',
        "14",
    )

    plan = build_group_27286_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "14"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AB=2AH=2AC\cos A=2\cdot 14\cdot 0{,}5=14" in solution


def test_group_27287_uses_direct_cosine_to_find_the_equal_side() -> None:
    """Use the inverse direct-cosine equation only for the requested equal side."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=28"></span>, '
        '<span data-inline-latex="\\cos A=0{,}7"></span>. '
        'Найдите <span data-inline-latex="AC"></span>.</p>',
        "20",
    )

    plan = build_group_27287_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "20"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}" in solution


def test_group_27287_accepts_parent_visible_base_assignment() -> None:
    """Accept the parent's semantic var element without weakening the rule."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AB">AB</var> = 8, '
        '<span data-inline-latex="\\cos A=0{,}5"></span>. '
        'Найдите <var data-math-identifier="AC">AC</var>.</p>',
        "8",
    )

    plan = build_group_27287_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == "8"


@pytest.mark.parametrize(
    ("side", "tangent", "current", "expected"),
    [
        (r"1{,}5", r"\frac{5}{\sqrt{20}}", "2", "2"),
        ("16", r"\frac{7}{3\sqrt{7}}", "24", "24"),
        ("7", r"\frac{33}{4\sqrt{33}}", "8", "8"),
    ],
)
def test_group_27288_finds_base_from_equal_side_and_tangent(
    side: str,
    tangent: str,
    current: str,
    expected: str,
) -> None:
    """Use the parent's tangent-to-cosine factor only in group 27288."""

    context = _context(
        f'<p><span data-inline-latex="AC=BC={side}"></span>, '
        f'<span data-inline-latex="\\tg A={tangent}"></span>. '
        'Найдите <span data-inline-latex="AB"></span>.</p>',
        current,
    )

    plan = build_group_27288_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AB=2AH=2AC\cos A=2AC\sqrt{\frac{1}{1+\tg^{2} A}}" in solution


def test_group_27288_does_not_replace_asset_of_task_with_solution() -> None:
    """Treat a task with an existing solution as content-owned by that task."""

    context = _context(
        '<p><span data-inline-latex="AC=BC=16"></span>, '
        '<span data-inline-latex="\\tg A=\\frac{7}{3\\sqrt{7}}"></span>. '
        'Найдите <span data-inline-latex="AB"></span>.</p>',
        "24",
        "<p>Существующее решение со своим рисунком.</p>",
    )
    context["normalized_content"]["assets"] = [  # type: ignore[index]
        {"asset_key": "image_1", "asset_id": "other-asset"}
    ]

    plan = build_group_27288_repair_plan(
        context,
        parent_condition_asset_id=PARENT_ASSET_ID,
    )

    assert plan.transformations == ()


@pytest.mark.parametrize(
    ("base", "tangent", "current", "expected"),
    [
        ("8", r"\frac{33}{4\sqrt{33}}", "7", "7"),
        ("24", r"\frac{8}{15}", "6,4", "13,6"),
        ("12", r"\frac{5}{\sqrt{20}}", "9", "9"),
    ],
)
def test_group_27289_finds_equal_side_from_base_and_tangent(
    base: str,
    tangent: str,
    current: str,
    expected: str,
) -> None:
    """Use only the inverse tangent contract and copy both parent diagrams."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\tg A={tangent}"></span>. '
        'Найдите <span data-inline-latex="AC"></span>.</p>',
        current,
    )

    plan = build_group_27289_repair_plan(
        context,
        parent_condition_asset_id="condition-asset",
        parent_solution_assets=PARENT_SOLUTION_ASSETS,
    )

    assert plan.answer == expected
    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    assert by_target["asset:image_1"]["value"]["asset_id"] == "condition-asset"
    assert by_target["asset:image_2"]["value"]["asset_id"] == PARENT_ASSET_ID
    solution = by_target["section:solution"]["value"]
    assert solution["asset_keys"] == ["image_2"]
    assert '<center><img alt=""' in solution["html"]
    assert r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}" in solution["html"]


def test_group_27289_preserves_existing_solution_and_its_assets() -> None:
    """Do not take ownership of content when the task already has a solution."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=12"></span>, '
        '<span data-inline-latex="\\tg A=\\frac{5}{\\sqrt{20}}"></span>. '
        'Найдите <span data-inline-latex="AC"></span>.</p>',
        "9",
        "<p>Существующее решение.</p>",
    )
    context["normalized_content"]["assets"] = [  # type: ignore[index]
        {"asset_key": "image_1", "asset_id": "own-condition"},
        {"asset_key": "image_7", "asset_id": "own-solution"},
    ]

    plan = build_group_27289_repair_plan(
        context,
        parent_condition_asset_id="condition-asset",
        parent_solution_assets=PARENT_SOLUTION_ASSETS,
    )

    assert plan.transformations == ()


@pytest.mark.parametrize(
    ("equal_sides", "base_name", "base", "angle", "sine", "altitude", "expected"),
    [
        ("AC=BC", "AB", "20", "BAC", r"0{,}8", "AH", "16"),
        ("AB=BC", "AC", "6", "ACB", r"\frac{3}{5}", "CH", "3,6"),
    ],
)
def test_group_27320_uses_base_sine_for_the_corresponding_altitude(
    equal_sides: str,
    base_name: str,
    base: str,
    angle: str,
    sine: str,
    altitude: str,
    expected: str,
) -> None:
    """Accept only the group's two label-equivalent geometric arrangements."""

    context = _context(
        f'<p><span data-inline-latex="{equal_sides}"></span>, '
        f'<span data-inline-latex="{base_name}={base}"></span>, '
        f'<span data-inline-latex="\\sin {angle}={sine}"></span>. '
        f'Найдите высоту <span data-inline-latex="{altitude}"></span>.</p>',
        ".",
    )
    solution_assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "altitude-diagram",
            "url": "/assets/altitude-diagram",
            "alt": "",
        },
    )

    plan = build_group_27320_repair_plan(
        context,
        parent_solution_assets=solution_assets,
    )

    assert plan.answer == expected
    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    assert by_target["asset:image_1"]["value"]["parent_target_id"] == "section:condition:1"
    assert by_target["section:solution"]["value"]["asset_keys"] == []
    assert f"{altitude}={base_name}\\sin" in by_target["section:solution"]["value"]["html"]


def test_group_27320_rejects_altitude_from_the_other_base_vertex() -> None:
    """Fail rather than silently solve a different labelled construction."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=20"></span>, '
        '<span data-inline-latex="\\sin BAC=0{,}8"></span>. '
        'Найдите высоту <span data-inline-latex="BH"></span>.</p>',
        "16",
    )

    with pytest.raises(IsoscelesTrianglePlanError, match="given base-angle vertex"):
        build_group_27320_repair_plan(
            context,
            parent_solution_assets=(),
        )


def test_group_27320_accepts_parent_visible_base_assignment() -> None:
    """Accept the parent's var-rendered base without weakening the contract."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AB">AB</var> = 8, '
        '<span data-inline-latex="\\sin BAC=0{,}5"></span>. '
        'Найдите высоту <var data-math-identifier="AH">AH</var>.</p>',
        "4",
        "<p>Существующее решение.</p>",
    )

    plan = build_group_27320_repair_plan(
        context,
        parent_solution_assets=(),
    )

    assert plan.answer == "4"
    assert plan.transformations == ()


@pytest.mark.parametrize(
    ("base", "sine", "expected"),
    [
        ("5", r"\frac{7}{25}", "4,8"),
        ("12", r"\frac{\sqrt{51}}{10}", "8,4"),
        ("8", r"\frac{\sqrt{7}}{4}", "6"),
    ],
)
def test_group_27321_finds_projection_from_base_and_sine(
    base: str,
    sine: str,
    expected: str,
) -> None:
    """Follow the parent cosine-from-sine proof for only the declared projection."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AH">AH</var> — высота, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\sin BAC={sine}"></span>. '
        'Найдите <var data-math-identifier="BH">BH</var>.</p>',
        ".",
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "projection-diagram",
            "url": "/assets/projection-diagram",
            "alt": "",
        },
    )

    plan = build_group_27321_repair_plan(context, parent_solution_assets=assets)

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"BH=AB\cos \angle ABH=AB\cos \angle BAC" in solution


def test_group_27321_rejects_requested_altitude_instead_of_projection() -> None:
    """Keep the output contract fixed to the segment from the other base endpoint."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AH">AH</var> — высота, '
        '<span data-inline-latex="AB=5"></span>, '
        '<span data-inline-latex="\\sin BAC=\\frac{7}{25}"></span>. '
        'Найдите <var data-math-identifier="AH">AH</var>.</p>',
        "1,4",
    )

    with pytest.raises(IsoscelesTrianglePlanError, match="projection segment"):
        build_group_27321_repair_plan(context, parent_solution_assets=())


@pytest.mark.parametrize(
    ("base", "cosine", "expected"),
    [
        ("5", r"\frac{7}{25}", "4,8"),
        ("25", r"\frac{3}{5}", "20"),
        ("8", r"\frac{\sqrt{7}}{4}", "6"),
    ],
)
def test_group_27322_finds_altitude_from_base_and_cosine(
    base: str,
    cosine: str,
    expected: str,
) -> None:
    """Follow only the parent's sine-from-cosine altitude proof."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\cos BAC={cosine}"></span>. '
        'Найдите высоту <span data-inline-latex="AH"></span>.</p>',
        ".",
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "cosine-altitude-diagram",
            "url": "/assets/cosine-altitude-diagram",
            "alt": "",
        },
    )

    plan = build_group_27322_repair_plan(context, parent_solution_assets=assets)

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AH=AB\sin \angle ABH=AB\sin \angle BAC" in solution
    assert r"\sqrt{1-\cos^{2} \angle BAC}" in solution


def test_group_27323_uses_cosine_directly_for_projection() -> None:
    """Do not derive sine when the requested projection is already adjacent."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AH">AH</var> — высота, '
        '<span data-inline-latex="AB=14"></span>, '
        '<span data-inline-latex="\\cos BAC=0{,}5"></span>. '
        'Найдите <var data-math-identifier="BH">BH</var>.</p>',
        "0",
    )

    plan = build_group_27323_repair_plan(
        context,
        parent_condition_asset_id="projection-condition",
    )

    assert plan.answer == "7"
    by_target = {item["transformation_target_id"]: item for item in plan.transformations}
    solution = by_target["section:solution"]["value"]["html"]
    assert r"BH=AB\cos \angle ABH=AB\cos \angle BAC=14\cdot 0{,}5=7" in solution
    assert r"\sin" not in solution


@pytest.mark.parametrize(
    ("base", "tangent", "expected"),
    [
        ("22", r"\frac{\sqrt{3}}{3}", "11"),
        (r"13{,}6", r"\frac{15}{8}", "12"),
        ("9", r"\frac{\sqrt{20}}{5}", "6"),
    ],
)
def test_group_27324_finds_altitude_from_base_and_tangent(
    base: str,
    tangent: str,
    expected: str,
) -> None:
    """Use the parent's cotangent identity only for group 27324."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\tg BAC={tangent}"></span>. '
        'Найдите высоту <span data-inline-latex="AH"></span>.</p>',
        ".",
    )

    plan = build_group_27324_repair_plan(
        context,
        parent_condition_asset_id="tangent-altitude-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AH=AB\sin \angle ABH=AB\sin \angle ABC" in solution
    assert r"\ctg^{2} \angle ABC" in solution


@pytest.mark.parametrize(
    ("base", "tangent", "current", "expected"),
    [
        (r"20{,}5", r"\frac{9}{40}", "20", "20"),
        (r"1{,}5", r"\frac{5}{\sqrt{20}}", "4", "1"),
        ("16", r"\frac{7}{3\sqrt{7}}", "12", "12"),
    ],
)
def test_group_27325_finds_projection_from_base_and_tangent(
    base: str,
    tangent: str,
    current: str,
    expected: str,
) -> None:
    """Use direct cosine-from-tangent and independently repair source answers."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<var data-math-identifier="AH">AH</var> — высота, '
        f'<span data-inline-latex="AB={base}"></span>, '
        f'<span data-inline-latex="\\tg BAC={tangent}"></span>. '
        'Найдите <var data-math-identifier="BH">BH</var>.</p>',
        current,
    )

    plan = build_group_27325_repair_plan(
        context,
        parent_condition_asset_id="tangent-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"BH=AB\cos \angle ABH=AB\cos \angle BAC" in solution


@pytest.mark.parametrize(
    ("side", "sine", "current", "expected"),
    [
        (r"4\sqrt{15}", r"0{,}25", "7,5", "7,5"),
        (r"8\sqrt{7}", r"0{,}75", "0", "21"),
    ],
)
def test_group_27326_finds_altitude_from_equal_side_and_sine(
    side: str,
    sine: str,
    current: str,
    expected: str,
) -> None:
    """Use the first parent proof and repair the answer independently."""

    context = _context(
        f'<p><span data-inline-latex="AC=BC={side}"></span>, '
        f'<span data-inline-latex="\\sin BAC={sine}"></span>. '
        'Найдите высоту <span data-inline-latex="AH"></span>.</p>',
        current,
    )

    plan = build_group_27326_repair_plan(
        context,
        parent_condition_asset_id="side-sine-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"2AC\sin \angle BAC\sqrt{1-\sin^{2} \angle BAC}" in solution


def test_group_27326_validates_existing_natural_language_side_form() -> None:
    """Accept the audited source wording used by existing solved tasks only."""

    context = _context(
        '<p>В равнобедренном треугольнике ABC с основанием AB боковая сторона '
        'равна <span data-inline-latex="16\\sqrt{15}"></span>, '
        '<span data-inline-latex="\\sin \\angle BAC=0{,}25"></span>. '
        'Найдите длину высоты <span data-inline-latex="AH"></span>.</p>',
        "30",
        "<p>Существующее решение.</p>",
    )

    plan = build_group_27326_repair_plan(
        context,
        parent_condition_asset_id="side-sine-condition",
    )

    assert plan.answer == "30"
    assert plan.transformations == ()


@pytest.mark.parametrize(
    ("side", "sine", "current", "expected"),
    [
        ("12", r"\frac{1}{2}", "18", "18"),
        ("72", r"\frac{1}{6}", "000", "140"),
    ],
)
def test_group_27327_finds_external_projection_from_equal_side_and_sine(
    side: str,
    sine: str,
    current: str,
    expected: str,
) -> None:
    """Use only the primary parent diagram and the short audited proof."""

    context = _context(
        f'<p><span data-inline-latex="AC=BC={side}"></span>, '
        '<span data-inline-latex="AH"></span> — высота, '
        f'<span data-inline-latex="\\sin BAC={sine}"></span>. '
        'Найдите <span data-inline-latex="BH"></span>.</p>',
        current,
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "primary-diagram",
            "url": "/assets/primary-diagram",
            "alt": "",
        },
        {
            "asset_key": "image_2",
            "source_asset_id": "source-note-diagram",
            "url": "/assets/source-note-diagram",
            "alt": "",
        },
    )

    plan = build_group_27327_repair_plan(
        context,
        parent_solution_assets=assets,
    )

    assert plan.answer == expected
    targets = [item["transformation_target_id"] for item in plan.transformations]
    assert "asset:image_1" in targets
    assert "asset:image_2" not in targets
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )
    assert solution["value"]["asset_keys"] == []
    assert r"2AC\cos^{2} \angle BAC=2AC(1-\sin^{2} \angle BAC)" in solution["value"]["html"]


@pytest.mark.parametrize(
    ("side", "cosine", "current", "expected"),
    [
        (r"8\sqrt{7}", r"0{,}75", "21", "21"),
        (r"16\sqrt{15}", r"0{,}25", "000", "30"),
    ],
)
def test_group_27328_finds_altitude_from_equal_side_and_cosine(
    side: str,
    cosine: str,
    current: str,
    expected: str,
) -> None:
    """Accept only the 27328 cosine input and altitude output contract."""

    context = _context(
        f'<p><span data-inline-latex="AC=BC={side}"></span>, '
        f'<span data-inline-latex="\\cos BAC={cosine}"></span>. '
        'Найдите высоту <span data-inline-latex="AH"></span>.</p>',
        current,
    )

    plan = build_group_27328_repair_plan(
        context,
        parent_condition_asset_id="side-cosine-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"2AC\cos \angle BAC\sqrt{1-\cos^{2} \angle BAC}" in solution


@pytest.mark.parametrize(
    ("side", "cosine", "expected"),
    [("30", r"\frac{2}{5}", "9,6"), ("25", r"\frac{3}{5}", "18")],
)
def test_group_27329_finds_projection_from_equal_side_and_cosine(
    side: str,
    cosine: str,
    expected: str,
) -> None:
    """Accept only the 27329 cosine input and BH output contract."""

    context = _context(
        f'<p><span data-inline-latex="AC=BC={side}"></span>, '
        '<span data-inline-latex="AH"></span> — высота, '
        f'<span data-inline-latex="\\cos BAC={cosine}"></span>. '
        'Найдите <span data-inline-latex="BH"></span>.</p>',
        "000",
    )

    plan = build_group_27329_repair_plan(
        context,
        parent_condition_asset_id="side-cosine-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"BH=AB\cos \angle ABH=AB\cos \angle BAC" in solution


def test_group_27330_finds_sine_from_altitude_and_base() -> None:
    """Accept only equal sides, AB and altitude AH with sine as the output."""

    context = _context(
        '<p>В треугольнике <span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=10"></span>, высота '
        '<span data-inline-latex="AH"></span> равна 8. '
        'Найдите синус угла <span data-inline-latex="BAC"></span>.</p>',
        "000",
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "sine-diagram",
            "url": "/assets/sine-diagram",
            "alt": "",
        },
    )

    plan = build_group_27330_repair_plan(context, parent_solution_assets=assets)

    assert plan.answer == "0,8"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )
    assert solution["value"]["asset_keys"] == []
    assert r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}" in solution["value"]["html"]


def test_group_27330_accepts_the_a_shorthand_and_relabelled_orientation() -> None:
    """Handle only the audited A shorthand and the group's second label orientation."""

    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "sine-diagram",
            "url": "/assets/sine-diagram",
            "alt": "",
        },
    )
    short_angle = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=10"></span>, высота '
        '<span data-inline-latex="AH"></span> равна 4. '
        'Найдите <span data-inline-latex="\\sin A"></span>.</p>',
        "0,4",
    )
    relabelled = _context(
        '<p><span data-inline-latex="AB=BC"></span>, '
        '<span data-inline-latex="AC=8"></span>, высота '
        '<span data-inline-latex="CH"></span> равна 4. '
        'Найдите синус угла <span data-inline-latex="ACB"></span>.</p>',
        "3",
    )

    first = build_group_27330_repair_plan(short_angle, parent_solution_assets=assets)
    second = build_group_27330_repair_plan(relabelled, parent_solution_assets=assets)

    assert first.answer == "0,4"
    assert second.answer == "0,5"
    second_solution = next(
        item for item in second.transformations if item["transformation_target_id"] == "section:solution"
    )
    assert second_solution["value"]["asset_keys"] == []
    assert r"\sin \angle ACB=\sin \angle BAC=\frac{CH}{AC}" in second_solution["value"]["html"]


@pytest.mark.parametrize(
    ("base", "altitude", "current", "expected"),
    [("25", "24", "0,28", "0,28"), ("15", "9", "0,75", "0,8")],
)
def test_group_27331_finds_cosine_from_altitude_and_base(
    base: str,
    altitude: str,
    current: str,
    expected: str,
) -> None:
    """Accept only the 27331 AB/AH input and cosine output contract."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, '
        f'<span data-inline-latex="AB={base}"></span>, высота '
        f'<span data-inline-latex="AH"></span> равна <span data-inline-latex="{altitude}"></span>. '
        'Найдите <span data-inline-latex="\\cos A"></span>.</p>',
        current,
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "cosine-diagram",
            "url": "/assets/cosine-diagram",
            "alt": "",
        },
    )

    plan = build_group_27331_repair_plan(context, parent_solution_assets=assets)

    assert plan.answer == expected
    if current != expected:
        assert any(
            item["transformation_target_id"] == "section:answer:1"
            for item in plan.transformations
        )


def test_group_27331_finds_sine_from_altitude_and_projection() -> None:
    """Accept the group's audited AH/BH to sine subtype and nothing implicit."""

    context = _context(
        '<p><span data-inline-latex="AC=BC"></span>, высота '
        '<span data-inline-latex="AH"></span> равна 15, '
        '<span data-inline-latex="BH=20"></span>. '
        'Найдите <span data-inline-latex="\\sin BAC"></span>.</p>',
        "000",
    )
    assets = (
        {
            "asset_key": "image_1",
            "source_asset_id": "cosine-diagram",
            "url": "/assets/cosine-diagram",
            "alt": "",
        },
    )

    plan = build_group_27331_repair_plan(context, parent_solution_assets=assets)

    assert plan.answer == "0,6"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AB=\sqrt{AH^{2}+BH^{2}}" in solution
    assert r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}" in solution


@pytest.mark.parametrize(
    ("side", "altitude", "current", "expected"),
    [("5", "1", "0,2", "0,2"), ("14", "7", "-", "0,5")],
)
def test_group_27345_finds_obtuse_vertex_sine_from_altitude(
    side: str,
    altitude: str,
    current: str,
    expected: str,
) -> None:
    """Use only the supplementary-angle sine relation allowed by group 27345."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        f'<span data-inline-latex="AC=BC={side}"></span>, высота '
        f'<span data-inline-latex="AH"></span> равна {altitude}. '
        'Найдите <span data-inline-latex="\\sin ACB"></span>.</p>',
        current,
    )

    plan = build_group_27345_repair_plan(
        context,
        parent_condition_asset_id="obtuse-sine-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\sin \angle ACB=\sin \angle ACH=\frac{AH}{AC}" in solution


@pytest.mark.parametrize(
    ("condition", "current", "expected", "relation"),
    [
        (
            '<span data-inline-latex="AC=BC=25"></span>, высота AH равна 20. '
            'Найдите <span data-inline-latex="\\cos ACB"></span>.',
            "-0,6",
            "-0,6",
            r"\cos \angle ACB=-\cos \angle ACH",
        ),
        (
            '<span data-inline-latex="AB=BC"></span>, '
            '<span data-inline-latex="AB=25"></span>, высота CH равна 7. '
            'Найдите косинус угла ABC.',
            "000",
            "-0,96",
            r"\cos \angle ABC=-\cos \angle CBH",
        ),
    ],
)
def test_group_27346_finds_obtuse_vertex_cosine_from_altitude(
    condition: str,
    current: str,
    expected: str,
    relation: str,
) -> None:
    """Accept only the two audited label orientations of group 27346."""

    plan = build_group_27346_repair_plan(
        _context(f"<p>В тупоугольном треугольнике {condition}</p>", current),
        parent_condition_asset_id="obtuse-cosine-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert relation in solution


@pytest.mark.parametrize(
    ("side", "altitude", "current", "expected"),
    [
        (r"\sqrt{41}", "4", "-0,8", "-0,8"),
        (r"2\sqrt{5}", "4", "000", "-2"),
    ],
)
def test_group_27347_finds_obtuse_vertex_tangent_from_altitude(
    side: str,
    altitude: str,
    current: str,
    expected: str,
) -> None:
    """Use only the supplementary-angle tangent relation allowed by 27347."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        f'<span data-inline-latex="AC=BC={side}"></span>, высота '
        f'<span data-inline-latex="AH"></span> равна {altitude}. '
        'Найдите <span data-inline-latex="\\tg ACB"></span>.</p>',
        current,
    )

    plan = build_group_27347_repair_plan(
        context,
        parent_condition_asset_id="obtuse-tangent-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\tg \angle ACB=\tg (\pi-\angle ACH)" in solution


@pytest.mark.parametrize(
    ("side", "projection", "current", "expected"),
    [("5", "1", "-0,2", "-0,2"), ("14", "7", "0", "-0,5")],
)
def test_group_27349_finds_obtuse_vertex_cosine_from_projection(
    side: str,
    projection: str,
    current: str,
    expected: str,
) -> None:
    """Use only the side/projection cosine relation allowed by 27349."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        f'<span data-inline-latex="AC=BC={side}"></span>, '
        '<span data-inline-latex="AH"></span> — высота, '
        f'<span data-inline-latex="CH={projection}"></span>. '
        'Найдите <span data-inline-latex="\\cos ACB"></span>.</p>',
        current,
    )

    plan = build_group_27349_repair_plan(
        context,
        parent_condition_asset_id="obtuse-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"-\cos \angle ACH=-\frac{HC}{AC}" in solution


@pytest.mark.parametrize(
    ("side", "projection", "current", "expected"),
    [
        (r"2\sqrt{5}", "4", "0,5", "-0,5"),
        (r"2\sqrt{26}", "10", "-0,2", "-0,2"),
    ],
)
def test_group_27350_finds_obtuse_vertex_tangent_from_projection(
    side: str,
    projection: str,
    current: str,
    expected: str,
) -> None:
    """Use only the side/projection tangent relation allowed by 27350."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        f'<span data-inline-latex="AC=BC={side}"></span>, '
        '<span data-inline-latex="AH"></span> — высота, '
        f'<span data-inline-latex="CH={projection}"></span>. '
        'Найдите <span data-inline-latex="\\tg ACB"></span>.</p>',
        current,
    )

    plan = build_group_27350_repair_plan(
        context,
        parent_condition_asset_id="obtuse-tangent-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"-\frac{AH}{CH}=-\frac{\sqrt{AC^{2}-CH^{2}}}{CH}" in solution


@pytest.mark.parametrize(
    ("altitude", "projection", "current", "expected"),
    [("10", r"5\sqrt{21}", "0,4", "0,4"), ("7", r"\sqrt{51}", "0", "0,7")],
)
def test_group_27351_finds_obtuse_vertex_sine_from_altitude_and_projection(
    altitude: str,
    projection: str,
    current: str,
    expected: str,
) -> None:
    """Use only the altitude/projection sine relation allowed by 27351."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        '<span data-inline-latex="AC=BC"></span>, '
        f'высота <span data-inline-latex="AH={altitude}"></span>, '
        f'<span data-inline-latex="CH={projection}"></span>. '
        'Найдите <span data-inline-latex="\\sin ACB"></span>.</p>',
        current,
    )

    plan = build_group_27351_repair_plan(
        context,
        parent_condition_asset_id="obtuse-sine-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AC=\sqrt{AH^{2}+CH^{2}}" in solution
    assert r"\sin \angle ACB=\sin (180^{\circ}-\angle ACH)" in solution


@pytest.mark.parametrize(
    ("altitude", "projection", "current", "expected"),
    [("20", "15", "000", "-0,6"), (r"9\sqrt{11}", "3", "-0,1", "-0,1")],
)
def test_group_27352_finds_obtuse_vertex_cosine_from_altitude_and_projection(
    altitude: str,
    projection: str,
    current: str,
    expected: str,
) -> None:
    """Use only the altitude/projection cosine relation allowed by 27352."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        '<span data-inline-latex="AC=BC"></span>, '
        f'высота <span data-inline-latex="AH={altitude}"></span>, '
        f'<span data-inline-latex="CH={projection}"></span>. '
        'Найдите <span data-inline-latex="\\cos ACB"></span>.</p>',
        current,
    )

    plan = build_group_27352_repair_plan(
        context,
        parent_condition_asset_id="obtuse-cosine-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AC=\sqrt{AH^{2}+CH^{2}}" in solution
    assert r"\cos \angle ACB=\cos (180^{\circ}-\angle ACH)" in solution


@pytest.mark.parametrize(
    ("altitude", "projection", "current", "expected"),
    [("1", "5", "-0,2", "-0,2"), ("2", "4", "-0.5", "-0,5")],
)
def test_group_27353_finds_obtuse_vertex_tangent_from_altitude_and_projection(
    altitude: str,
    projection: str,
    current: str,
    expected: str,
) -> None:
    """Use only the direct altitude/projection tangent relation allowed by 27353."""

    context = _context(
        '<p>В тупоугольном треугольнике '
        '<span data-inline-latex="AC=BC"></span>, '
        f'высота <span data-inline-latex="AH={altitude}"></span>, '
        f'<span data-inline-latex="CH={projection}"></span>. '
        'Найдите <span data-inline-latex="\\tg ACB"></span>.</p>',
        current,
    )

    plan = build_group_27353_repair_plan(
        context,
        parent_condition_asset_id="obtuse-tangent-projection-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"-\tg \angle ACH=-\frac{AH}{CH}" in solution
    assert "sqrt" not in solution


@pytest.mark.parametrize(
    ("condition", "current", "expected"),
    [
        (
            'Угол при вершине, противоположной основанию равнобедренного треугольника, '
            'равен <span data-inline-latex="30^{\\circ}"></span>. '
            'Боковая сторона треугольника равна 3.',
            "2,25",
            "2,25",
        ),
        (
            'В равнобедренном треугольнике <span data-inline-latex="ABC"></span> '
            'угол C равен 30°. Боковые стороны '
            '<span data-inline-latex="AC=BC=14"></span>.',
            "000",
            "49",
        ),
    ],
)
def test_group_27589_finds_area_from_side_and_30_degree_vertex_angle(
    condition: str,
    current: str,
    expected: str,
) -> None:
    """Accept only the two audited phrasings of the fixed area contract."""

    context = _context(
        f"<p>{condition} Найдите площадь этого треугольника.</p>",
        current,
    )
    plan = build_group_27589_repair_plan(
        context,
        parent_condition_asset_id="area-condition",
    )

    assert plan.answer == expected
    if not any(section["key"] == "solution" for section in context["normalized_content"]["sections"]):
        solution = next(
            item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
        )["value"]["html"]
        assert r"S=\frac{1}{2}a^{2}\sin 30^{\circ}" in solution


@pytest.mark.parametrize(
    ("side", "current", "expected"),
    [("25", "156,25", "156,25"), ("13", ".", "42,25")],
)
def test_group_27590_finds_area_from_side_and_150_degree_vertex_angle(
    side: str,
    current: str,
    expected: str,
) -> None:
    """Accept only the fixed 150-degree area contract."""

    context = _context(
        '<p>Угол при вершине, противоположной основанию равнобедренного '
        'треугольника, равен <span data-inline-latex="150^{\\circ}"></span>. '
        f'Боковая сторона треугольника равна {side}. '
        'Найдите площадь этого треугольника.</p>',
        current,
    )
    plan = build_group_27590_repair_plan(
        context,
        parent_condition_asset_id="obtuse-area-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\sin 150^{\circ}" in solution
    assert r"\sin 30^{\circ}" in solution


@pytest.mark.parametrize(
    ("side", "base", "current", "expected"),
    [("5", "6", "12", "12"), ("203", "294", ".", "20580")],
)
def test_group_27619_finds_area_from_side_and_base(
    side: str,
    base: str,
    current: str,
    expected: str,
) -> None:
    """Accept only an equal side and base with area as the requested result."""

    context = _context(
        f"<p>Боковая сторона равнобедренного треугольника равна {side}, "
        f"а основание равно {base}. Найдите площадь этого треугольника.</p>",
        current,
    )
    plan = build_group_27619_repair_plan(
        context,
        parent_condition_asset_id="area-from-sides-condition",
    )

    assert plan.answer == expected
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"h=\sqrt{a^{2}-\left(\frac{b}{2}\right)^{2}}" in solution
    assert r"S=\frac{1}{2}bh" in solution


def test_group_27620_finds_side_from_area_and_30_degree_vertex_angle() -> None:
    """Use only the fixed angle and area to recover the equal side."""

    context = _context(
        '<p>Угол при вершине, противоположной основанию равнобедренного '
        'треугольника, равен <span data-inline-latex="30^{\\circ}"></span>. '
        'Найдите боковую сторону треугольника, если его площадь равна 1444.</p>',
        ".",
    )
    plan = build_group_27620_repair_plan(
        context,
        parent_condition_asset_id="side-from-area-condition",
    )

    assert plan.answer == "76"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"S=\frac{1}{2}a^{2}\sin 30^{\circ}=\frac{a^{2}}{4}" in solution
    assert r"a=2\sqrt{S}" in solution


def test_group_27621_finds_side_from_area_and_150_degree_vertex_angle() -> None:
    """Preserve the supplementary-angle step for the fixed 150-degree contract."""

    context = _context(
        '<p>Угол при вершине, противоположной основанию равнобедренного '
        'треугольника, равен <span data-inline-latex="150^{\\circ}"></span>. '
        'Найдите боковую сторону треугольника, если его площадь равна 576.</p>',
        ".",
    )
    plan = build_group_27621_repair_plan(
        context,
        parent_condition_asset_id="obtuse-side-from-area-condition",
    )

    assert plan.answer == "48"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\sin 150^{\circ}" in solution
    assert r"\sin 30^{\circ}" in solution


def test_group_27744_finds_vertex_angle_from_one_base_angle() -> None:
    """Use equal base angles and the triangle angle sum for group 27744."""

    context = _context(
        '<p>В треугольнике ABC угол A равен <span data-inline-latex="5^{\\circ}"></span>, '
        '<span data-inline-latex="AC=BC"></span>. Найдите угол C. Ответ дайте в градусах.</p>',
        "000",
    )
    plan = build_group_27744_repair_plan(
        context,
        parent_condition_asset_id="vertex-angle-condition",
    )

    assert plan.answer == "170"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle A=\angle B=5^{\circ}" in solution
    assert r"180^{\circ}-2\cdot 5^{\circ}=170^{\circ}" in solution


def test_group_27744_accepts_verbal_equal_side_statement() -> None:
    """Accept the audited verbal AC and BC equality without widening the contract."""

    context = _context(
        '<p>В треугольнике ABC угол A равен 42°, стороны AC и BC равны. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "96",
    )

    plan = build_group_27744_repair_plan(
        context,
        parent_condition_asset_id="vertex-angle-condition",
    )

    assert plan.answer == "96"


def test_group_27744_moves_existing_solution_image_before_attaching_it_to_condition() -> None:
    """Order relocation writes so the solution rewrite cannot remove the new condition usage."""

    context = _context(
        '<p>В треугольнике ABC угол A равен 42°, стороны AC и BC равны. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "96",
        '<p><img data-asset-key="image_1" src="/assets/old"/>Готовое решение.</p>',
    )
    context["normalized_content"]["assets"] = [
        {"asset_key": "image_1", "asset_id": "old", "url": "/assets/old"}
    ]
    context["normalized_content"]["sections"][-1]["asset_keys"] = ["image_1"]

    plan = build_group_27744_repair_plan(
        context,
        parent_condition_asset_id="vertex-angle-condition",
    )

    assert [item["transformation_target_id"] for item in plan.transformations[:2]] == [
        "section:solution:1",
        "asset:image_1",
    ]


def test_group_27744_attaches_condition_image_without_rewriting_existing_solution() -> None:
    """Repair a missing condition diagram independently of substantive solution text."""

    context = _context(
        '<p>В треугольнике ABC угол A равен 42°, стороны AC и BC равны. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "96",
        "<p>Готовое решение.</p>",
    )

    plan = build_group_27744_repair_plan(
        context,
        parent_condition_asset_id="vertex-angle-condition",
    )

    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1"
    ]


def test_group_27745_finds_base_angle_from_vertex_angle() -> None:
    """Halve the remainder after subtracting the vertex angle."""

    context = _context(
        '<p>В треугольнике ABC угол C равен <span data-inline-latex="20^{\\circ}"></span>, '
        '<span data-inline-latex="AC=BC"></span>. Найдите угол A. Ответ дайте в градусах.</p>',
        "160",
    )
    plan = build_group_27745_repair_plan(
        context,
        parent_condition_asset_id="base-angle-condition",
    )

    assert plan.answer == "80"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\frac{180^{\circ}-20^{\circ}}{2}=80^{\circ}" in solution


def test_group_27746_finds_exterior_base_angle() -> None:
    """Recover the base angle first and then use its supplementary exterior angle."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'угол C равен <span data-inline-latex="60^{\\circ}"></span>. '
        'Найдите внешний угол CBD. Ответ дайте в градусах.</p>',
        "133",
    )
    plan = build_group_27746_repair_plan(
        context,
        parent_condition_asset_id="exterior-angle-condition",
    )

    assert plan.answer == "120"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle B=\frac{180^{\circ}-\angle C}{2}" in solution
    assert r"\angle CBD=180^{\circ}-\angle B" in solution


def test_group_27746_accepts_verbal_equal_side_statement() -> None:
    """Accept the audited verbal equality for the same exterior-angle contract."""

    context = _context(
        '<p>В треугольнике ABC стороны AC и BC равны, угол C равен 120°, '
        'угол CBD — внешний. Найдите внешний угол CBD.</p>',
        "150",
        "<p>Готовое решение.</p>",
    )

    assert build_group_27746_repair_plan(
        context,
        parent_condition_asset_id="exterior-angle-condition",
    ).answer == "150"


def test_group_27747_finds_vertex_angle_from_exterior_base_angle() -> None:
    """Convert the exterior angle to a base angle before using the angle sum."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>. '
        'Внешний угол при вершине B равен <span data-inline-latex="164^{\\circ}"></span>. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "108",
    )
    plan = build_group_27747_repair_plan(
        context,
        parent_condition_asset_id="vertex-from-exterior-condition",
    )

    assert plan.answer == "148"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle B=180^{\circ}-164^{\circ}=16^{\circ}" in solution
    assert r"\angle C=180^{\circ}-2\angle B" in solution


def test_group_27748_finds_base_angle_from_exterior_vertex_angle() -> None:
    """Halve the exterior angle when it is at the vertex between equal sides."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AB=BC"></span>. '
        'Внешний угол при вершине B равен <span data-inline-latex="18^{\\circ}"></span>. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "81",
    )
    plan = build_group_27748_repair_plan(
        context,
        parent_condition_asset_id="base-from-exterior-vertex-condition",
    )

    assert plan.answer == "9"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle B=180^{\circ}-18^{\circ}=162^{\circ}" in solution
    assert r"\frac{180^{\circ}-162^{\circ}}{2}=9^{\circ}" in solution


def test_group_27750_finds_smaller_angle_from_larger_angle() -> None:
    """Treat a unique larger angle as the vertex angle and halve the remainder."""

    context = _context(
        '<p>Больший угол равнобедренного треугольника равен '
        '<span data-inline-latex="130^{\\circ}"></span>. '
        'Найдите меньший угол. Ответ дайте в градусах.</p>',
        "0000",
    )
    plan = build_group_27750_repair_plan(
        context,
        parent_condition_asset_id="smaller-angle-condition",
    )

    assert plan.answer == "25"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\frac{180^{\circ}-130^{\circ}}{2}=25^{\circ}" in solution


def test_group_27754_finds_smaller_angle_from_difference() -> None:
    """Use two equal smaller angles and one larger vertex angle."""

    context = _context(
        '<p>Один угол равнобедренного треугольника на '
        '<span data-inline-latex="165^{\\circ}"></span> больше другого. '
        'Найдите меньший угол. Ответ дайте в градусах.</p>',
        ".",
    )
    plan = build_group_27754_repair_plan(
        context,
        parent_condition_asset_id="difference-angle-condition",
    )

    assert plan.answer == "5"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"2x+(x+165)=180\iff 3x=15\iff x=5" in solution


def test_group_27760_finds_vertex_angle_from_altitude_angle() -> None:
    """Use the right subtriangle and equal base angles to recover the vertex angle."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AD"></span> — высота, угол BAD равен '
        '<span data-inline-latex="2^{\\circ}"></span>. Найдите угол C.</p>',
        "14",
    )
    plan = build_group_27760_repair_plan(
        context,
        parent_condition_asset_id="altitude-angle-condition",
    )

    assert plan.answer == "4"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle B=90^{\circ}-\angle BAD" in solution
    assert r"\angle C=180^{\circ}-2\angle B" in solution


def test_group_27792_finds_equilateral_triangle_height() -> None:
    """Adapt the parent height computation to the task's exact side length."""

    context = _context(
        '<p>В треугольнике ABC '
        '<span data-inline-latex="AB=BC=AC=70\\sqrt{3}"></span>. '
        'Найдите высоту CH.</p>',
        "105",
    )
    plan = build_group_27792_repair_plan(
        context,
        parent_condition_asset_id="equilateral-height-condition",
    )

    assert plan.answer == "105"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"CH=AC\sin \angle A" in solution
    assert r"70\sqrt{3}\cdot \frac{\sqrt{3}}{2}=105" in solution


def test_group_27793_finds_equilateral_triangle_side() -> None:
    """Invert the parent height formula for an equilateral triangle."""

    context = _context(
        '<p>В равностороннем треугольнике ABC высота CH равна '
        '<span data-inline-latex="4\\sqrt{3}"></span>. '
        'Найдите стороны этого треугольника.</p>',
        "8",
    )
    plan = build_group_27793_repair_plan(
        context,
        parent_condition_asset_id="equilateral-side-condition",
    )

    assert plan.answer == "8"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AC=\frac{CH}{\sin \angle A}" in solution
    assert r"4\sqrt{3}\cdot \frac{2}{\sqrt{3}}=8" in solution


def test_group_27794_recovers_the_equilateral_vertex_angle() -> None:
    """Use the median half-base and Pythagoras before identifying 60 degrees."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        '<span data-inline-latex="AB=40"></span>, высота CH равна '
        '<span data-inline-latex="20\\sqrt{3}"></span>. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "000",
    )
    plan = build_group_27794_repair_plan(
        context,
        parent_condition_asset_id="equilateral-angle-condition",
    )

    assert plan.answer == "60"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AH=\frac{AB}{2}=20" in solution
    assert r"AC=\sqrt{AH^{2}+CH^{2}}" in solution
    assert "равносторонний" in solution


def test_group_27795_finds_altitude_from_equal_side_and_vertex_angle() -> None:
    """Use the task's actual vertex angle rather than hard-coding 30 degrees."""

    context = _context(
        '<p>В треугольнике ABC '
        '<span data-inline-latex="AC=BC=2\\sqrt{2}"></span>, '
        'угол C равен <span data-inline-latex="45^{\\circ}"></span>. '
        'Найдите высоту <span data-inline-latex="AH"></span>.</p>',
        "2",
    )
    plan = build_group_27795_repair_plan(
        context,
        parent_condition_asset_id="side-angle-altitude-condition",
    )

    assert plan.answer == "2"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AH=AC\sin \angle C" in solution
    assert r"2\sqrt{2}\cdot \frac{\sqrt{2}}{2}=2" in solution


def test_group_27796_finds_acute_vertex_angle_from_side_and_altitude() -> None:
    """Recover the requested acute angle directly from its sine."""

    context = _context(
        '<p>В остроугольном треугольнике ABC известно, что '
        '<span data-inline-latex="AC=BC=66"></span>, высота AH равна 33. '
        'Найдите угол C. Ответ дайте в градусах.</p>',
        "30",
    )
    plan = build_group_27796_repair_plan(
        context,
        parent_condition_asset_id="side-altitude-angle-condition",
    )

    assert plan.answer == "30"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\sin \angle C=\frac{AH}{AC}=\frac{33}{66}=\frac{1}{2}" in solution
    assert r"\angle C=30^{\circ}" in solution


def test_group_27797_finds_equal_side_from_altitude_and_vertex_angle() -> None:
    """Invert the altitude sine relation using the exact task values."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'высота AH равна 5, угол C равен '
        '<span data-inline-latex="30^{\\circ}"></span>. Найдите AC.</p>',
        "10",
    )
    plan = build_group_27797_repair_plan(
        context,
        parent_condition_asset_id="altitude-angle-side-condition",
    )

    assert plan.answer == "10"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"AC=\frac{AH}{\sin \angle C}" in solution
    assert r"\frac{5}{\sin 30^{\circ}}=5\cdot 2=10" in solution


def test_group_27798_finds_altitude_for_obtuse_vertex_angle() -> None:
    """Use the supplementary angle in the exterior right subtriangle."""

    context = _context(
        '<p>В треугольнике ABC '
        '<span data-inline-latex="AC=BC=2\\sqrt{2}"></span>, угол C равен '
        '<span data-inline-latex="135^{\\circ}"></span>. Найдите высоту AH.</p>',
        "2",
    )
    plan = build_group_27798_repair_plan(
        context,
        parent_condition_asset_id="obtuse-side-angle-altitude-condition",
    )

    assert plan.answer == "2"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\angle ACH=180^{\circ}-\angle C=45^{\circ}" in solution
    assert r"2\sqrt{2}\cdot \frac{\sqrt{2}}{2}=2" in solution


def test_group_27799_finds_equal_side_by_the_cosine_rule() -> None:
    """Solve the isosceles triangle from its base and included vertex angle."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'угол C равен <span data-inline-latex="120^\\circ,\\quad AB=2\\sqrt{3}"></span> '
        'Найдите AC.</p>',
        "2",
    )
    plan = build_group_27799_repair_plan(
        context,
        parent_condition_asset_id="base-angle-side-condition",
    )

    assert plan.answer == "2"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"=2AC^{2}\left(1-\cos \angle C\right)" in solution
    assert r"AC=\sqrt{\frac{AB^{2}}{2\left(1-\cos \angle C\right)}}" in solution
    assert r"\sqrt{\frac{(2\sqrt{3})^{2}}{3}}=2" in solution


def test_group_27800_finds_base_by_the_cosine_rule() -> None:
    """Compute the base from equal sides and their included angle."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'угол C равен <span data-inline-latex="120^{\\circ}"></span>, '
        '<span data-inline-latex="AC=3\\sqrt{3}"></span>. Найдите AB.</p>',
        "9",
    )
    plan = build_group_27800_repair_plan(
        context,
        parent_condition_asset_id="side-angle-base-condition",
    )

    assert plan.answer == "9"
    solution = next(
        item for item in plan.transformations if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]
    assert r"\cos \angle C=\cos 120^{\circ}=- \frac{1}{2}" in solution
    assert r"AB^{2}=AC^{2}+BC^{2}-2AC\cdot BC\cos \angle C" in solution
    assert r"\iff AB^{2}=27+27-2\cdot 27\cdot(- \frac{1}{2})" in solution
    assert r"\iff AB^{2}=27+27+27" in solution
    assert r"\iff AB^{2}=81" in solution
    assert r"AB=\sqrt{81}=9" in solution


def test_group_27800_refreshes_an_existing_solution_without_rewriting_the_answer() -> None:
    """Replace this group's older proof while preserving an already correct answer."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'угол C равен <span data-inline-latex="120^{\\circ}"></span>, '
        '<span data-inline-latex="AC=3\\sqrt{3}"></span>. Найдите AB.</p>',
        "9",
        solution="<p>Старое сокращённое решение.</p>",
    )
    plan = build_group_27800_repair_plan(
        context,
        parent_condition_asset_id="side-angle-base-condition",
    )

    targets = [item["transformation_target_id"] for item in plan.transformations]
    assert "section:solution:1" in targets
    assert "section:answer:1" not in targets


def test_group_27800_does_not_parse_equal_side_name_as_length() -> None:
    """Skip AC=BC when selecting the separately supplied AC length."""

    context = _context(
        '<p>В треугольнике ABC <span data-inline-latex="AC=BC"></span>, '
        'угол C равен <span data-inline-latex="120^{\\circ}"></span>, '
        '<span data-inline-latex="AC=2\\sqrt{3}"></span>. Найдите AB.</p>',
        "6",
        solution="<p>Содержательное решение уже есть.</p>",
    )
    plan = build_group_27800_repair_plan(
        context,
        parent_condition_asset_id="side-angle-base-condition",
    )

    assert plan.answer == "6"
    assert not any(
        item["transformation_target_id"] == "section:solution"
        for item in plan.transformations
    )


def test_group_628232_verifies_base_from_equal_side_and_tangent() -> None:
    """Compute the base and preserve an existing substantive solution."""

    context = _context(
        '<p>В треугольнике ABC известно, что AC=BC=15, '
        '<span data-inline-latex="\\tg \\angle A=2\\sqrt{6}"></span>. '
        'Найдите длину стороны AB.</p>',
        "6",
        solution="<p>Содержательное решение уже есть.</p>",
    )
    plan = build_group_628232_repair_plan(
        context,
        parent_condition_asset_id="condition-asset",
        parent_solution_assets=(
            {
                "asset_key": "image_2",
                "source_asset_id": "solution-asset",
                "url": "/assets/solution-asset",
                "alt": "",
            },
        ),
    )

    assert plan.answer == "6"
    assert plan.transformations == ()


def test_group_676342_verifies_base_angle_from_exterior_angle() -> None:
    """Compute the requested base angle and preserve an existing solution."""

    context = _context(
        '<p>Внешний угол CBD (при вершине В) равнобедренного треугольника АВС '
        'с основанием АВ равен 126°. Найдите величину угла А треугольника АВС.</p>',
        "54",
        solution="<p>Содержательное решение уже есть.</p>",
    )
    plan = build_group_676342_repair_plan(
        context,
        parent_condition_asset_id="condition-asset",
    )

    assert plan.answer == "54"
    assert plan.transformations == ()


def test_group_701874_verifies_base_angle_from_apex_exterior_angle() -> None:
    """Halve the apex exterior angle and preserve an existing solution."""

    context = _context(
        '<p>В равнобедренном треугольнике ABC с основанием AB внешний угол '
        'при вершине C равен 34°. Найдите величину угла ABC.</p>',
        "17",
        solution="<p>Содержательное решение уже есть.</p>",
    )
    plan = build_group_701874_repair_plan(
        context,
        parent_condition_asset_id="condition-asset",
    )

    assert plan.answer == "17"
    assert plan.transformations == ()
